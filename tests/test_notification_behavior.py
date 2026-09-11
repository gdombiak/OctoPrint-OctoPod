from unittest.mock import Mock

import pytest

import octoprint_octopod.paused_for_user as paused_module
from octoprint_octopod.job_notifications import JobNotifications
from octoprint_octopod.layer_notifications import LayerNotifications
from octoprint_octopod.paused_for_user import PausedForUser

from conftest import FakePrinter, FakeSettings


@pytest.fixture
def logger():
	return Mock()


@pytest.fixture
def ifttt():
	return Mock()


def test_layer_notification_fires_for_a_permanent_layer(logger, ifttt, plugin_manager):
	notifications = LayerNotifications(logger, ifttt, plugin_manager)
	notifications._send_base_notification = Mock(return_value=True)
	settings = FakeSettings({"notify_layers": [2, 5]})

	notifications.layer_changed(settings, "5")

	ifttt.fire_event.assert_called_once_with(settings, "layer-changed", "5")
	notifications._send_base_notification.assert_called_once_with(
		settings,
		True,
		"layer_changed",
		event_param={"PrintLayer": "5"},
	)


def test_layer_notification_ignores_unconfigured_layers(logger, ifttt, plugin_manager):
	notifications = LayerNotifications(logger, ifttt, plugin_manager)
	notifications._send_base_notification = Mock()
	settings = FakeSettings({"notify_layers": [2, 5]})

	notifications.layer_changed(settings, "4")

	ifttt.fire_event.assert_not_called()
	notifications._send_base_notification.assert_not_called()


def test_temporary_layers_can_be_added_removed_and_reset(logger, ifttt, plugin_manager):
	notifications = LayerNotifications(logger, ifttt, plugin_manager)

	notifications.add_layer("7")
	notifications.add_layer("10")
	assert notifications.get_layers() == ["7", "10"]

	notifications.remove_layer("7")
	assert notifications.get_layers() == ["10"]

	notifications.reset_layers()
	assert notifications.get_layers() == []


@pytest.mark.parametrize(
	("progress_type", "progress", "expected"),
	[
		("0", 50, False),
		("25", 25, True),
		("25", 50, True),
		("25", 75, True),
		("25", 26, False),
		("50", 49.6, True),
		("50", 75, False),
		("100", 50, False),
	],
)
def test_progress_notifications_follow_configured_thresholds(
	logger, ifttt, plugin_manager, progress_type, progress, expected
):
	notifications = JobNotifications(logger, ifttt, plugin_manager)
	notifications._send_base_notification = Mock(return_value=True)
	settings = FakeSettings({"progress_type": progress_type})
	printer = FakePrinter(completion=progress)

	notifications.on_print_progress(settings, progress, printer)

	assert notifications._send_base_notification.called is expected
	assert ifttt.fire_event.called is expected


def test_print_time_genius_progress_is_used_when_plugin_is_enabled(logger, ifttt, plugin_manager):
	plugin_manager.plugins["PrintTimeGenius"] = type("Plugin", (), {"enabled": True})()
	notifications = JobNotifications(logger, ifttt, plugin_manager)
	notifications._send_base_notification = Mock(return_value=True)
	settings = FakeSettings({"progress_type": "50"})
	printer = FakePrinter(completion=20, print_time=60, print_time_left=60)

	notifications.on_print_progress(settings, 20, printer)

	ifttt.fire_event.assert_called_once_with(settings, "print-progress", 50)


def test_pause_gcode_notifies_once_per_interval(monkeypatch, logger, ifttt, plugin_manager):
	clock = Mock(return_value=1_000.0)
	monkeypatch.setattr(paused_module.time, "time", clock)
	notifications = PausedForUser(logger, ifttt, plugin_manager)
	notifications._snooze_end_time = 0
	notifications._send_base_notification = Mock(return_value=True)
	settings = FakeSettings({"pause_interval": 5})
	printer = FakePrinter(completion=40, printing=True)

	notifications.process_sent_gcode(settings, printer, "M600")
	clock.return_value = 1_001.0
	notifications.process_sent_gcode(settings, printer, "M600")
	clock.return_value = 1_301.0
	notifications.process_sent_gcode(settings, printer, "M600")

	assert notifications._send_base_notification.call_count == 2
	assert ifttt.fire_event.call_count == 2


def test_pause_notification_requires_an_active_print(monkeypatch, logger, ifttt, plugin_manager):
	monkeypatch.setattr(paused_module.time, "time", Mock(return_value=1_000.0))
	notifications = PausedForUser(logger, ifttt, plugin_manager)
	notifications._snooze_end_time = 0
	notifications._send_base_notification = Mock()
	settings = FakeSettings({"pause_interval": 5})
	printer = FakePrinter(completion=0, printing=False)

	notifications.process_sent_gcode(settings, printer, "M600")

	notifications._send_base_notification.assert_not_called()
	ifttt.fire_event.assert_not_called()


def test_zero_pause_interval_disables_notifications(monkeypatch, logger, ifttt, plugin_manager):
	monkeypatch.setattr(paused_module.time, "time", Mock(return_value=1_000.0))
	notifications = PausedForUser(logger, ifttt, plugin_manager)
	notifications._snooze_end_time = 0
	notifications._send_base_notification = Mock()
	settings = FakeSettings({"pause_interval": 0})
	printer = FakePrinter(completion=40, printing=True)

	notifications.process_received_gcode(settings, printer, "echo:busy: paused for user")

	notifications._send_base_notification.assert_not_called()
	ifttt.fire_event.assert_not_called()


def test_snooze_suppresses_pause_notification(monkeypatch, logger, ifttt, plugin_manager):
	clock = Mock(return_value=1_000.0)
	monkeypatch.setattr(paused_module.time, "time", clock)
	notifications = PausedForUser(logger, ifttt, plugin_manager)
	notifications._send_base_notification = Mock()
	settings = FakeSettings({"pause_interval": 5})
	printer = FakePrinter(completion=40, printing=True)

	notifications.snooze(10)
	clock.return_value = 1_100.0
	notifications.process_received_gcode(settings, printer, "// action:paused")

	notifications._send_base_notification.assert_not_called()
	ifttt.fire_event.assert_not_called()


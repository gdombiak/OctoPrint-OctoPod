from unittest.mock import Mock

from octoprint.events import Events

from octoprint_octopod import OctopodPlugin
from octoprint_octopod.job_notifications import JobNotifications
from octoprint_octopod.live_activities import LiveActivities

from conftest import FakePrinter, FakeSettings


def test_printer_state_event_is_handled_before_after_startup():
	plugin = OctopodPlugin()
	plugin._logger = Mock()
	plugin._settings = FakeSettings(plugin.get_settings_defaults())
	plugin._plugin_manager = Mock(plugins={})
	plugin._printer = FakePrinter()

	plugin.initialize()

	assert isinstance(plugin._job_notifications, JobNotifications)
	assert isinstance(plugin._live_activities, LiveActivities)
	plugin._plugin_manager.register_message_receiver.assert_not_called()
	assert plugin._checkTempTimer is None

	plugin._job_notifications.send_print_job_notification = Mock(
		wraps=plugin._job_notifications.send_print_job_notification
	)
	plugin._live_activities.on_printer_state_changed = Mock(
		wraps=plugin._live_activities.on_printer_state_changed
	)
	payload = {"state_id": "OPERATIONAL", "state_string": "Operational"}

	plugin.on_event(Events.PRINTER_STATE_CHANGED, payload)

	plugin._job_notifications.send_print_job_notification.assert_called_once_with(
		plugin._settings, plugin._printer, payload
	)
	plugin._live_activities.on_printer_state_changed.assert_called_once_with(
		plugin._settings, plugin._printer, payload
	)

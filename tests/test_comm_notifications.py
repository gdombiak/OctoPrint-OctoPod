from threading import Event, Thread, get_ident
from unittest.mock import Mock

import pytest
import requests

from octoprint_octopod import OctopodPlugin
from octoprint_octopod.http_client import REQUEST_TIMEOUT

from conftest import FakePrinter, FakeSettings, wait_for_notifications


@pytest.fixture
def plugin(plugin_manager, notification_worker):
	plugin = OctopodPlugin()
	plugin._logger = Mock()
	plugin._notification_worker = notification_worker
	plugin._plugin_manager = plugin_manager
	plugin._printer = FakePrinter(completion=40, printing=True)
	values = plugin.get_settings_defaults()
	values.update(
		tokens=[{"apnsToken": "test-token", "printerID": "test-printer",
				 "printerName": "Printer", "languageCode": "en"}],
		ifttt_key="test-key", ifttt_name="Printer",
	)
	plugin._settings = FakeSettings(values)
	plugin.initialize()
	plugin._paused_for_user._snooze_end_time = 0
	plugin._mmu_assitance._snooze_end_time = 0
	return plugin


def trigger_notification(plugin, trigger):
	if trigger.startswith("M"):
		return plugin.process_sent_gcode(None, "sent", trigger, None, trigger)
	if trigger == "mmu":
		line = "mmu_get_response - begin move: T-code"
		assert plugin.process_received_gcode(None, line) == line
		trigger = "mmu_get_response() returning: 0"
	assert plugin.process_received_gcode(None, trigger) == trigger


@pytest.mark.parametrize("trigger", [
	"M600", "M601", "M25", "M0", "M1",
	"echo:busy: paused for user", "// action:paused", "mmu",
])
@pytest.mark.parametrize("blocked_target", ["push", "ifttt"])
def test_hooks_return_while_http_is_blocked(monkeypatch, plugin, trigger, blocked_target):
	entered, release, returned = Event(), Event(), Event()
	hook_threads, request_threads, errors = [], [], []

	def post(url, **kwargs):
		request_threads.append(get_ident())
		assert kwargs["timeout"] == REQUEST_TIMEOUT
		is_ifttt = "maker.ifttt.com" in url
		if is_ifttt == (blocked_target == "ifttt"):
			entered.set()
			assert release.wait(5), "Test did not release blocked HTTP request"
		return Mock(status_code=200 if is_ifttt else 204)

	post_mock = Mock(side_effect=post)
	monkeypatch.setattr(requests, "post", post_mock)

	def invoke_hook():
		hook_threads.append(get_ident())
		try:
			trigger_notification(plugin, trigger)
		except BaseException as error:
			errors.append(error)
		finally:
			returned.set()

	hook = Thread(target=invoke_hook, daemon=True)
	try:
		hook.start()
		assert entered.wait(2), "Notification did not reach HTTP delivery"
		assert returned.wait(2), "Communication hook blocked on HTTP delivery"
		assert not errors
		assert set(request_threads).isdisjoint(hook_threads)
		# Receive-loop parsing must continue while delivery is still blocked.
		assert plugin.process_received_gcode(None, "ok") == "ok"
	finally:
		release.set()
		hook.join(timeout=2)
		wait_for_notifications(plugin._notification_worker)

	assert not hook.is_alive()
	assert post_mock.call_count == 2  # IFTTT and APNS each delivered once.
	push_payload = post_mock.call_args_list[-1][1]["json"]
	assert push_payload["tokens"] == ["test-token"]
	assert push_payload["message"] == (
		"MMU Requires User Assistance" if trigger == "mmu" else "Printer paused for user"
	)


def test_sent_and_received_pause_reports_are_deduplicated(monkeypatch, plugin):
	post = Mock(return_value=Mock(status_code=204))
	monkeypatch.setattr(requests, "post", post)
	start = Event()
	errors = []

	def invoke(trigger):
		try:
			assert start.wait(2)
			trigger_notification(plugin, trigger)
		except BaseException as error:
			errors.append(error)

	threads = [Thread(target=invoke, args=(trigger,)) for trigger in ("M601", "// action:paused")]
	for thread in threads:
		thread.start()
	start.set()
	for thread in threads:
		thread.join(timeout=2)
		assert not thread.is_alive()
	wait_for_notifications(plugin._notification_worker)

	assert not errors
	assert post.call_count == 2


def test_new_pause_after_resuming_delivers_again(monkeypatch, plugin):
	post = Mock(return_value=Mock(status_code=204))
	monkeypatch.setattr(requests, "post", post)
	trigger_notification(plugin, "M601")
	plugin.process_sent_gcode(None, "sent", "G1 X10", None, "G1")
	trigger_notification(plugin, "M601")
	wait_for_notifications(plugin._notification_worker)
	assert post.call_count == 4


@pytest.mark.parametrize("disabled", ["interval", "snooze"])
def test_mmu_notification_can_be_disabled(monkeypatch, plugin, disabled):
	post = Mock()
	monkeypatch.setattr(requests, "post", post)
	if disabled == "interval":
		plugin._settings.set(["mmu_interval"], 0)
	else:
		plugin._mmu_assitance.snooze(10)
	trigger_notification(plugin, "mmu")
	wait_for_notifications(plugin._notification_worker)
	post.assert_not_called()


def test_plugin_shutdown_stops_notification_submission(plugin):
	plugin.on_shutdown()
	assert not plugin._notification_worker.submit(Mock())


@pytest.mark.parametrize("error", [requests.ConnectTimeout, requests.ReadTimeout])
def test_ifttt_timeout_still_allows_push_delivery(monkeypatch, plugin, error):
	delivered = Event()

	def post(url, **kwargs):
		if "maker.ifttt.com" in url:
			raise error("IFTTT timed out")
		delivered.set()
		return Mock(status_code=204)

	post_mock = Mock(side_effect=post)
	monkeypatch.setattr(requests, "post", post_mock)
	trigger_notification(plugin, "M601")
	wait_for_notifications(plugin._notification_worker)
	assert post_mock.call_count == 2
	assert post_mock.call_args[0][0].endswith("/v1/push_printer")
	assert delivered.is_set()


@pytest.mark.parametrize("error", [requests.ConnectTimeout, requests.ReadTimeout])
def test_failed_push_does_not_prevent_a_later_notification(monkeypatch, plugin, error):
	plugin._settings.set(["ifttt_key"], "")
	post = Mock(side_effect=[error("Push timed out"), Mock(status_code=204)])
	monkeypatch.setattr(requests, "post", post)
	trigger_notification(plugin, "M601")
	plugin.process_sent_gcode(None, "sent", "G1 X10", None, "G1")
	trigger_notification(plugin, "M601")
	wait_for_notifications(plugin._notification_worker)
	assert post.call_count == 2
	assert not plugin._notification_worker._stopped.is_set()


def test_legacy_mmu_notification_is_delivered_by_worker(monkeypatch, plugin):
	plugin._settings.set(["tokens"], [{"apnsToken": "legacy-token", "printerID": "legacy-printer"}])
	post = Mock(return_value=Mock(status_code=204))
	monkeypatch.setattr(requests, "post", post)
	trigger_notification(plugin, "mmu")
	wait_for_notifications(plugin._notification_worker)
	assert post.call_count == 2
	assert post.call_args[0][0].endswith("/v1/push_printer/code_events")
	assert post.call_args[1]["json"]["printerID"] == "legacy-printer"
	assert post.call_args[1]["json"]["eventCode"] == "mmu-event"

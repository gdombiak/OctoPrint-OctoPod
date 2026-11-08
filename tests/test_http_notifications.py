import json
from unittest.mock import Mock

import pytest
import requests

from octoprint_octopod.alerts import Alerts
from octoprint_octopod.http_client import REQUEST_TIMEOUT
from octoprint_octopod.ifttt_notifications import IFTTTAlerts

from conftest import FakeSettings


URL = "http://notification-server.test/push"


def send_alert(alerts, variant):
	settings = FakeSettings({"sound_notification": "custom"})
	if variant.startswith("alert"):
		image = b"image-data" if variant.endswith("image") else None
		return alerts.send_alert_code(settings, "en", "token", URL, "Printer", "paused-user-event",
			category="category", image=image, apns_dict={"extra": "value"})
	if variant.startswith("job"):
		image = b"image-data" if variant.endswith("image") else None
		return alerts.send_job_request("token", image, "printer", "PRINTING", 50, URL)
	if variant == "bed":
		return alerts.send_bed_request(URL, "token", "printer", "bed-cooled", 30, 5)
	if variant == "mmu":
		return alerts.send_mmu_request(URL, "token", "printer")
	if variant == "live":
		return alerts.send_live_activity_notification(URL, ["token"], "PRINTING", 50, 60, True, 10)
	raise AssertionError("Unknown test variant")


VARIANTS = ["alert", "alert-image", "job", "job-image", "bed", "mmu", "live"]


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("status", [204, 503])
def test_push_requests_have_timeouts_and_preserve_payloads(monkeypatch, variant, status):
	post = Mock(return_value=Mock(status_code=status, content=b"response"))
	monkeypatch.setattr(requests, "post", post)
	alerts = Alerts(Mock())

	assert send_alert(alerts, variant) == status
	post.assert_called_once()
	assert post.call_args[0] == (URL,)
	kwargs = post.call_args[1]
	assert kwargs["timeout"] == (3.05, 10) == REQUEST_TIMEOUT
	if variant.endswith("image"):
		assert kwargs["files"]["image"] == ("image.jpg", b"image-data", "image/jpeg")
		payload = json.loads(kwargs["files"]["json"][1])
	else:
		payload = kwargs["json"]
	assert payload["tokens"] == ["token"]
	assert payload["useDev"] == alerts._use_dev
	if variant.startswith("alert"):
		assert payload["message"] == "Printer paused for user"
		assert payload["sound"] == "custom"
		assert payload["title"] == "Printer"
		assert payload["category"] == "category"
		assert payload["extra"] == "value"
	elif variant.startswith("job"):
		assert payload["printerState"] == "PRINTING"
		assert payload["printerCompletion"] == 50
		assert payload["silent"] is True
	elif variant == "bed":
		assert payload["eventCode"] == "bed-cooled"
		assert payload["temperature"] == 30
		assert payload["minutes"] == 5
	elif variant == "mmu":
		assert payload["eventCode"] == "mmu-event"
	elif variant == "live":
		assert payload["printerStatus"] == "PRINTING"
		assert payload["completion"] == 50
		assert payload["printTimeLeft"] == 60


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("error", [requests.ConnectTimeout, requests.ReadTimeout])
def test_push_timeouts_return_failure_instead_of_escaping(monkeypatch, variant, error):
	post = Mock(side_effect=error("Request timed out"))
	monkeypatch.setattr(requests, "post", post)
	assert send_alert(Alerts(Mock()), variant) == -500
	assert post.call_args[1]["timeout"] == REQUEST_TIMEOUT


@pytest.mark.parametrize("status", [200, 503])
def test_ifttt_request_preserves_payload_and_has_timeout(monkeypatch, status):
	post = Mock(return_value=Mock(status_code=status))
	monkeypatch.setattr(requests, "post", post)
	settings = FakeSettings({"ifttt_key": "key", "ifttt_name": "Printer"})
	IFTTTAlerts(Mock()).fire_event(settings, "paused-for-user", "value")
	post.assert_called_once_with(
		"https://maker.ifttt.com/trigger/octopod-paused-for-user/with/key/key",
		json={"value1": "Printer", "value2": "value", "value3": ""},
		timeout=REQUEST_TIMEOUT,
	)


@pytest.mark.parametrize("error", [requests.ConnectTimeout, requests.ReadTimeout])
def test_ifttt_timeout_is_handled(monkeypatch, error):
	monkeypatch.setattr(requests, "post", Mock(side_effect=error("Request timed out")))
	logger = Mock()
	settings = FakeSettings({"ifttt_key": "key", "ifttt_name": "Printer"})
	IFTTTAlerts(logger).fire_event(settings, "paused-for-user", "")
	logger.warning.assert_called_once()

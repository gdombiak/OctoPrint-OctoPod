from unittest.mock import Mock

import octoprint_octopod
from octoprint_octopod import OctopodPlugin

from conftest import FakeSettings


def make_plugin(monkeypatch, tokens):
	plugin = OctopodPlugin()
	plugin._settings = FakeSettings({"tokens": tokens})
	events = Mock()
	monkeypatch.setattr(octoprint_octopod, "eventManager", Mock(return_value=events))
	return plugin, events


def assert_settings_updated(plugin, events):
	assert plugin._settings.save_count == 1
	events.fire.assert_called_once_with(octoprint_octopod.Events.SETTINGS_UPDATED)


def test_registers_a_new_device(monkeypatch):
	plugin, events = make_plugin(monkeypatch, [])

	plugin.update_token("", "new-token", "Gaston's iPhone", "printer-1", "MK4", "en")

	assert plugin._settings.values["tokens"] == [
		{
			"apnsToken": "new-token",
			"deviceName": "Gaston's iPhone",
			"date": plugin._settings.values["tokens"][0]["date"],
			"printerID": "printer-1",
			"printerName": "MK4",
			"languageCode": "en",
		}
	]
	assert plugin._settings.values["tokens"][0]["date"]
	assert_settings_updated(plugin, events)


def test_recovers_from_missing_token_storage(monkeypatch):
	plugin, events = make_plugin(monkeypatch, None)

	plugin.update_token("", "new-token", "iPad", "printer-1", None, None)

	assert [token["apnsToken"] for token in plugin._settings.values["tokens"]] == ["new-token"]
	assert_settings_updated(plugin, events)


def test_replaces_an_existing_token_and_updates_device_metadata(monkeypatch):
	plugin, events = make_plugin(
		monkeypatch,
		[
			{
				"apnsToken": "old-token",
				"deviceName": "iPhone",
				"date": "old-date",
				"printerID": "printer-1",
			}
		],
	)

	plugin.update_token("old-token", "new-token", "iPhone", "printer-1", "MINI", "es")

	token = plugin._settings.values["tokens"][0]
	assert token["apnsToken"] == "new-token"
	assert token["printerName"] == "MINI"
	assert token["languageCode"] == "es"
	assert token["date"] != "old-date"
	assert_settings_updated(plugin, events)


def test_unchanged_registration_does_not_write_settings(monkeypatch):
	token = {
		"apnsToken": "same-token",
		"deviceName": "iPhone",
		"date": "existing-date",
		"printerID": "printer-1",
		"printerName": "MK4",
		"languageCode": "en",
	}
	plugin, events = make_plugin(monkeypatch, [token])

	plugin.update_token("same-token", "same-token", "iPhone", "printer-1", "MK4", "en")

	assert plugin._settings.save_count == 0
	events.fire.assert_not_called()
	assert plugin._settings.values["tokens"][0]["date"] == "existing-date"


def test_same_apns_token_can_be_registered_for_another_printer(monkeypatch):
	plugin, events = make_plugin(
		monkeypatch,
		[
			{
				"apnsToken": "shared-token",
				"deviceName": "iPhone",
				"date": "existing-date",
				"printerID": "printer-1",
			}
		],
	)

	plugin.update_token("shared-token", "shared-token", "iPhone", "printer-2", "XL", "en")

	assert [token["printerID"] for token in plugin._settings.values["tokens"]] == ["printer-1", "printer-2"]
	assert_settings_updated(plugin, events)


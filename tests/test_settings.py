from octoprint_octopod import OctopodPlugin

from conftest import FakeSettings


def test_settings_defaults_are_safe_to_mutate():
	plugin = OctopodPlugin()

	first = plugin.get_settings_defaults()
	second = plugin.get_settings_defaults()
	first["tokens"].append("changed")

	assert second["tokens"] == []
	assert plugin.get_settings_version() == 15


def test_migration_from_version_14_preserves_layer_notification_meaning():
	plugin = OctopodPlugin()
	plugin._settings = FakeSettings({"notify_first_X_layers": 3})

	plugin.on_settings_migrate(target=15, current=14)

	# The old setting notified after layers 1-3 were printed. The replacement
	# notifies when layers 2-4 are reached, which represents the same moments.
	assert plugin._settings.values["notify_layers"] == [2, 3, 4]
	assert plugin._settings.values["bed_warm_notify_once"] is False
	assert plugin._settings.values["turn_HA_light_on_ifneeded"] is True


def test_new_install_migration_populates_defaults_and_copies_webcam_settings():
	plugin = OctopodPlugin()
	plugin._settings = FakeSettings(
		global_values={
			"webcam": {"flipH": True, "flipV": False, "rotate90": True},
		}
	)

	plugin.on_settings_migrate(target=15, current=None)

	assert plugin._settings.values["temp_interval"] == 5
	assert plugin._settings.values["progress_type"] == "50"
	assert plugin._settings.values["webcam_flipH"] is True
	assert plugin._settings.values["webcam_flipV"] is False
	assert plugin._settings.values["webcam_rotate90"] is True
	assert plugin._settings.values["notify_layers"] == [2]


def test_migration_only_changes_settings_added_after_current_version():
	plugin = OctopodPlugin()
	plugin._settings = FakeSettings(
		{
			"progress_type": "25",
			"notify_first_X_layers": 2,
		}
	)

	plugin.on_settings_migrate(target=15, current=14)

	assert plugin._settings.values["progress_type"] == "25"
	assert plugin._settings.values["notify_layers"] == [2, 3]


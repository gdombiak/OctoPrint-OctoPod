# coding=utf-8
from __future__ import absolute_import

import datetime
import flask
import logging
import octoprint.plugin
import sys
from octoprint.access.permissions import Permissions
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer

from .bed_notifications import BedNotifications
from .custom_notifications import CustomNotifications
from .gcode_notifications import GcodeNotifications
from .ifttt_notifications import IFTTTAlerts
from .job_notifications import JobNotifications
from .layer_notifications import LayerNotifications
from .libs.sbc import SBCFactory, RPi
from .mmu import MMUAssistance
from .palette2 import Palette2Notifications
from .paused_for_user import PausedForUser
from .soc_temp_notifications import SocTempNotifications
from .test_notifications import TestNotifications
from .thermal_protection_notifications import ThermalProtectionNotifications
from .tools_notifications import ToolsNotifications

# Plugin that stores FCM tokens reported from Android devices to know which Android devices to alert
# when print is done or other relevant events

debug_soc_temp = False


class PrintoidPlugin(octoprint.plugin.SettingsPlugin,
					 octoprint.plugin.AssetPlugin,
					 octoprint.plugin.TemplatePlugin,
					 octoprint.plugin.StartupPlugin,
					 octoprint.plugin.SimpleApiPlugin,
					 octoprint.plugin.EventHandlerPlugin,
					 octoprint.plugin.ProgressPlugin):

	def __init__(self):
		super(PrintoidPlugin, self).__init__()
		self._logger = logging.getLogger("octoprint.plugins.printoid")
		self._checkTempTimer = None
		self._ifttt_alerts = IFTTTAlerts(self._logger)
		self._job_notifications = JobNotifications(self._logger, self._ifttt_alerts)
		self._tool_notifications = ToolsNotifications(self._logger, self._ifttt_alerts)
		self._bed_notifications = BedNotifications(self._logger, self._ifttt_alerts)
		self._mmu_assitance = MMUAssistance(self._logger, self._ifttt_alerts)
		self._paused_for_user = PausedForUser(self._logger, self._ifttt_alerts)
		self._palette2 = Palette2Notifications(self._logger, self._ifttt_alerts)
		self._layerNotifications = LayerNotifications(self._logger, self._ifttt_alerts)
		self._gcode_notifications = GcodeNotifications(self._logger, self._ifttt_alerts)
		self._test_notifications = TestNotifications(self._logger)
		self._check_soc_temp_timer = None
		self._soc_timer_interval = 5.0 if debug_soc_temp else 30.0
		self._soc_temp_notifications = SocTempNotifications(self._logger, self._ifttt_alerts,
															self._soc_timer_interval,
															debug_soc_temp)
		self._custom_notifications = CustomNotifications(self._logger)
		self._thermal_protection_notifications = ThermalProtectionNotifications(self._logger,
																				self._ifttt_alerts)

	# StartupPlugin mixin

	def on_after_startup(self):
		self._logger.info("Printoid loaded!")
		# Set logging level to what we have in the settings
		if self._settings.get_boolean(["debug_logging"]):
			self._logger.setLevel(logging.DEBUG)
		else:
			self._logger.setLevel(logging.INFO)

		# Register to listen for messages from other plugins
		self._plugin_manager.register_message_receiver(self.on_plugin_message)

		# Start timer that will check bed temperature and send notifications if needed
		self._restart_timer()

		# if running on linux then check soc temperature
		if sys.platform.startswith("linux") or debug_soc_temp:
			sbc = RPi(self._logger) if debug_soc_temp else SBCFactory().factory(self._logger)
			if sbc.is_supported:
				self._soc_temp_notifications.sbc = sbc
				sbc.debugMode = debug_soc_temp
				self._soc_temp_notifications.send_plugin_message = self.send_plugin_message
				self.start_soc_timer(self._soc_timer_interval)

	# SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			debug_logging=False,
			server_url='https://europe-west1-firebase-printoid.cloudfunctions.net/printoidPluginGateway-v2',
			camera_snapshot_url='http://127.0.0.1:8080/?action=snapshot',
			tokens=[],
			sound_notification='default',
			temp_interval=5,
			tool0_low=0,
			tool0_target_temp=False,
			bed_low=30,
			bed_target_temp_hold=10,
			mmu_interval=5,
			pause_interval=5,
			palette2_printing_error_codes=[103, 104, 111, 121],
			progress_type='50',
			# 0=disabled, 5=every 5%, 10=every 10%, 25=every 25%, 50=every 50%, 100=only when finished
			ifttt_key='',
			ifttt_name='',
			soc_temp_high=75,
			thermal_runway_threshold=10,
			thermal_threshold_minutes_frequency=10,
			thermal_cooldown_seconds_threshold=14,
			thermal_warmup_bed_seconds_threshold=19,
			thermal_warmup_hotend_seconds_threshold=39,
			thermal_warmup_chamber_seconds_threshold=19,
			thermal_below_target_threshold=5,
			webcam_flipH=False,
			webcam_flipV=False,
			webcam_rotate90=False,
			notify_first_X_layers=1,
			print_complete_delay_seconds=0
		)

	def on_settings_save(self, data):
		old_debug_logging = self._settings.get_boolean(["debug_logging"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_debug_logging = self._settings.get_boolean(["debug_logging"])
		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._logger.setLevel(logging.DEBUG)
			else:
				self._logger.setLevel(logging.INFO)

	def get_settings_version(self):
		return 14

	def on_settings_migrate(self, target, current):
		if current is None or current == 1:
			# add the 2 new values included
			self._settings.set(['temp_interval'], self.get_settings_defaults()["temp_interval"])
			self._settings.set(['bed_low'], self.get_settings_defaults()["bed_low"])

		if current is None or current <= 2:
			self._settings.set(['bed_target_temp_hold'],
							   self.get_settings_defaults()["bed_target_temp_hold"])

		if current is None or current <= 3:
			self._settings.set(['mmu_interval'], self.get_settings_defaults()["mmu_interval"])

		if current is None or current <= 4:
			self._settings.set(['pause_interval'], self.get_settings_defaults()["pause_interval"])

		if current is None or current <= 5:
			self._settings.set(['tool0_low'], self.get_settings_defaults()["tool0_low"])

		if current is None or current <= 6:
			self._settings.set(['palette2_printing_error_codes'],
							   self.get_settings_defaults()["palette2_printing_error_codes"])

		if current is None or current <= 7:
			self._settings.set(['progress_type'], self.get_settings_defaults()["progress_type"])

		if current is None or current <= 8:
			self._settings.set(['ifttt_key'], self.get_settings_defaults()["ifttt_key"])
			self._settings.set(['ifttt_name'], self.get_settings_defaults()["ifttt_name"])

		if current is None or current <= 9:
			self._settings.set(['soc_temp_high'], self.get_settings_defaults()["soc_temp_high"])
			self._settings.set(['webcam_flipH'], self._settings.global_get(["webcam", "flipH"]))
			self._settings.set(['webcam_flipV'], self._settings.global_get(["webcam", "flipV"]))
			self._settings.set(['webcam_rotate90'],
							   self._settings.global_get(["webcam", "rotate90"]))

		if current is None or current <= 10:
			self._settings.set(['tool0_target_temp'],
							   self.get_settings_defaults()["tool0_target_temp"])

		if current is None or current <= 11:
			self._settings.set(['thermal_runway_threshold'],
							   self.get_settings_defaults()["thermal_runway_threshold"])
			self._settings.set(['thermal_threshold_minutes_frequency'],
							   self.get_settings_defaults()["thermal_threshold_minutes_frequency"])
			self._settings.set(['sound_notification'],
							   self.get_settings_defaults()["sound_notification"])

		if current is None or current <= 12:
			self._settings.set(['thermal_cooldown_seconds_threshold'],
							   self.get_settings_defaults()["thermal_cooldown_seconds_threshold"])
			self._settings.set(['thermal_below_target_threshold'],
							   self.get_settings_defaults()["thermal_below_target_threshold"])
			self._settings.set(['thermal_warmup_bed_seconds_threshold'],
							   self.get_settings_defaults()["thermal_warmup_bed_seconds_threshold"])
			self._settings.set(['thermal_warmup_hotend_seconds_threshold'],
							   self.get_settings_defaults()[
								   "thermal_warmup_hotend_seconds_threshold"])
			self._settings.set(['thermal_warmup_chamber_seconds_threshold'],
							   self.get_settings_defaults()[
								   "thermal_warmup_chamber_seconds_threshold"])

		if current is None or current <= 13:
			self._settings.set(['notify_first_X_layers'],
							   self.get_settings_defaults()["notify_first_X_layers"])

		if current is None or current <= 14:
			self._settings.set(['server_url'],
							   self.get_settings_defaults()["server_url"])

	# AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/printoid.js"],
			css=["css/printoid.css"],
		)

	# ProgressPlugin

	# progress-hook
	def on_print_progress(self, storage, path, progress):
		# progress 0 - 100
		self._job_notifications.on_print_progress(self._settings, self._printer, progress)

	# EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == Events.PRINTER_STATE_CHANGED:
			self._job_notifications.send__printer_state_changed(self._settings, self._printer,
																payload)
		elif event == "DisplayLayerProgress_layerChanged":
			# Event sent from DisplayLayerProgress plugin when there was a detected layer changed
			self._layerNotifications.layer_changed(self._settings, payload["currentLayer"])

	# SimpleApiPlugin mixin

	def update_token(self, old_token, new_token, device_name, printer_id, printer_name):
		self._logger.debug("Received tokens for %s." % device_name)

		existing_tokens = self._settings.get(["tokens"])

		# Safety check in case a user manually modified config.yaml and left invalid JSON
		if existing_tokens is None:
			existing_tokens = []

		found = False
		updated = False
		for token in existing_tokens:
			# Check if existing token has been updated
			if token["fcmToken"] == old_token and token["printerID"] == printer_id:
				if old_token != new_token:
					self._logger.debug("Updating token for %s." % device_name)
					# Token that exists needs to be updated with new token
					token["fcmToken"] = new_token
					token["date"] = datetime.datetime.now().strftime("%x %X")
					updated = True
				found = True
			elif token["fcmToken"] == new_token and token["printerID"] == printer_id:
				found = True

			if found:
				if printer_name is not None and (
						"printerName" not in token or token["printerName"] != printer_name):
					# Printer name in Printoid has been updated
					token["printerName"] = printer_name
					token["date"] = datetime.datetime.now().strftime("%x %X")
					updated = True
				break

		if not found:
			self._logger.debug("Adding token for %s." % device_name)
			# Token was not found so we need to add it
			existing_tokens.append(
				{'fcmToken': new_token, 'deviceName': device_name,
				 'date': datetime.datetime.now().strftime("%x %X"),
				 'printerID': printer_id, 'printerName': printer_name})
			updated = True
		if updated:
			# Save new settings
			self._settings.set(["tokens"], existing_tokens)
			self._settings.save()
			eventManager().fire(Events.SETTINGS_UPDATED)
			self._logger.debug("Tokens saved")

	def get_api_commands(self):
		return dict(updateToken=["oldToken", "newToken", "deviceName", "printerID"],
					test=[],
					snooze=["eventCode", "minutes"],
					addLayer=["layer"],
					removeLayer=["layer"],
					getLayers=[],
					clearLayers=[],
					addGcodeCommand=["gcodeCommand"],
					removeGcodeCommand=["gcodeCommand"],
					getGcodeCommands=[],
					clearGcodeCommands=[],
					progressMode=["mode"],
					headTemperature=["temperature"],
					bedTemperature=["temperature"],
					bedWarmDuration=["minutes"],
					printerPausedDuration=["minutes"],
					socTemperatureThreshold=["temperature"],
					soundOption=["sound"],
					thermalProtection=["maxTempDiff", "bedShouldIncTemp", "hotendShouldIncTemp",
									   "chamberShouldIncTemp", "delayBetweenNotif"],
					getSoCTemps=[])

	def on_api_command(self, command, data):
		# Use this permission (as good as any other) to see if user can use this plugin and read status
		if not Permissions.CONNECTION.can():
			return flask.make_response("Insufficient rights", 403)

		if command == 'updateToken':
			# Convert from ASCII to UTF-8 since some chars will fail otherwise (e.g. apostrophe) - Only for Python 2
			if sys.version_info[0] == 2:
				data["deviceName"] = data["deviceName"].encode("utf-8")
			printer_name = data["printerName"] if 'printerName' in data else None

			self.update_token("{oldToken}".format(**data), "{newToken}".format(**data),
							  "{deviceName}".format(**data),
							  "{printerID}".format(**data), printer_name)

		elif command == 'test':
			code = self._test_notifications.send__test(self._settings)
			return flask.jsonify(dict(code=code))

		elif command == "progressMode":
			modeChanged = self._job_notifications.set_progress_mode(self._settings, data["mode"])
			if modeChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response("changing progress mode failed: unknown mode", 400)

		elif command == 'snooze':
			if data["eventCode"] == 'mmu-event':
				self._mmu_assitance.snooze(data["minutes"])
			else:
				return flask.make_response("Snooze command for unknown event", 400)

		elif command == 'addLayer':
			self._layerNotifications.add_layer(data["layer"])

		elif command == 'removeLayer':
			self._layerNotifications.remove_layer(data["layer"])

		elif command == 'clearLayers':
			self._layerNotifications.reset_layers()

		elif command == 'getLayers':
			return flask.jsonify(dict(layers=self._layerNotifications.get_layers()))

		elif command == 'addGcodeCommand':
			self._gcode_notifications.add_gcode_commands(data["gcodeCommand"])

		elif command == 'removeGcodeCommand':
			self._gcode_notifications.remove_gcode_commands(data["gcodeCommand"])

		elif command == 'clearGcodeCommands':
			self._gcode_notifications.reset_gcode_commands()

		elif command == 'getGcodeCommands':
			return flask.jsonify(
				dict(gcode_commands=self._gcode_notifications.get_gcode_commands()))

		elif command == 'getSoCTemps':
			return flask.jsonify(self._soc_temp_notifications.get_soc_temps())

		elif command == 'headTemperature':
			headTempChanged = self._tool_notifications.set_temperature_threshold(self._settings,
																				 data[
																					 "temperature"])
			if headTempChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response(
					"changing head temperature trigger failed: wrong temperature value", 400)

		elif command == 'bedTemperature':
			bedTempChanged = self._bed_notifications.set_temperature_threshold(self._settings,
																			   data["temperature"])
			if bedTempChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response(
					"changing bed temperature trigger failed: wrong temperature value", 400)

		elif command == 'bedWarmDuration':
			bedTimeChanged = self._bed_notifications.set_temperature_duration(self._settings,
																			  data["minutes"])
			if bedTimeChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response(
					"changing bed warm duration failed: wrong temperature value", 400)

		elif command == 'printerPausedDuration':
			printerPausedDurationChanged = self._paused_for_user.set_printer_pause_duration(
				self._settings, data["minutes"])
			if printerPausedDurationChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response("changing printer paused duration failed: wrong value",
										   400)

		elif command == 'socTemperatureThreshold':
			socTempThresholdChanged = self._soc_temp_notifications.set_soc_temperature_threshold(
				self._settings, data["temperature"])
			if socTempThresholdChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response("changing SoC temperature threshold failed: wrong value",
										   400)

		elif command == 'thermalProtection':
			thermalProtectionChanged = self._thermal_protection_notifications.set_thermal_protection(
				self._settings,
				data["maxTempDiff"],
				data["bedShouldIncTemp"],
				data["hotendShouldIncTemp"],
				data["chamberShouldIncTemp"],
				data["delayBetweenNotif"])
			if thermalProtectionChanged == True:
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response("changing thermal protection failed: wrong value", 400)

		elif command == 'soundOption':
			sound = data["sound"]
			if sound == 'default' or sound == 'sound-1.mp3' or sound == 'sound-2.mp3' or sound == 'sound-3.mp3':
				self._settings.set(["sound_notification"], sound)
				self._settings.save()
				eventManager().fire(Events.SETTINGS_UPDATED)
			else:
				return flask.make_response("changing sound option failed failed: wrong value", 400)

		else:
			return flask.make_response("Unknown command", 400)

	# TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", name="Printoid Notifications", custom_bindings=True)
		]

	# Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			printoid=dict(
				displayName="Printoid Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="anthonyst91",
				repo="OctoPrint-Printoid",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/anthonyst91/OctoPrint-Printoid/archive/{target_version}.zip"
			)
		)

	# Plugin messages

	def on_plugin_message(self, plugin, data, permissions=None):
		self._palette2.check_plugin_message(self._settings, plugin, data)

	def send_plugin_message(self, data):
		self._plugin_manager.send_plugin_message(self._identifier, data)

	# Timer functions

	def _restart_timer(self):
		# stop the timer
		if self._checkTempTimer:
			self._logger.debug(u"Stopping Timer...")
			self._checkTempTimer.cancel()
			self._checkTempTimer = None

		# start a new timer
		interval = self._settings.get_int(['temp_interval'])
		if interval:
			self._logger.debug(u"Starting Timer...")
			self._checkTempTimer = RepeatedTimer(interval, self.run_timer_job, None, None, True)
			self._checkTempTimer.start()

	def run_timer_job(self):
		self._bed_notifications.check_temps(self._settings, self._printer)
		self._tool_notifications.check_temps(self._settings, self._printer)
		self._thermal_protection_notifications.check_temps(self._settings, self._printer)

	def start_soc_timer(self, interval):
		self._logger.debug(u"Monitoring SoC temp with Timer")
		self._check_soc_temp_timer = RepeatedTimer(interval, self.update_soc_temp, run_first=True)
		self._check_soc_temp_timer.start()

	def update_soc_temp(self):
		self._soc_temp_notifications.check_soc_temp(self._settings)

	# GCODE hook

	def process_received_gcode(self, comm, line, *args, **kwargs):
		line = self._paused_for_user.process_gcode(self._settings, self._printer, line)
		self._thermal_protection_notifications.process_gcode(line)
		return self._mmu_assitance.process_gcode(self._settings, line)

	def process_sent_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		return self._gcode_notifications.process_gcode(self._settings, gcode)

	# Helper functions

	def push_notification(self, message, image=None):
		"""
		Send arbitrary push notification to Printoid app running on Android device
		via the Printoid FCM service.

		:param message: (String) Message to include in the notification
		:param image: Optional. (PIL Image) Image to include in the notification
		:return: True if the notification was successfully sent
		"""
		return self._custom_notifications.send_notification(self._settings, message, image)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Printoid Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrintoidPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.process_received_gcode,
		"octoprint.comm.protocol.gcode.sent": __plugin_implementation__.process_sent_gcode
	}

	global __plugin_helpers__
	__plugin_helpers__ = {
		"fcm_notification": __plugin_implementation__.push_notification
	}

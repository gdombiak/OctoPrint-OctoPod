# coding=utf-8
from __future__ import absolute_import

import datetime
import logging

import flask

import octoprint.plugin
from octoprint.events import eventManager, Events
from octoprint.server import user_permission
from octoprint.util import RepeatedTimer
from .job_notifications import JobNotifications
from .bed_notifications import BedNotifications
from .tools_notifications import ToolsNotifications
from .mmu import MMUAssistance
from .paused_for_user import PausedForUser
from .palette2 import Palette2Notifications
from .layer_notifications import LayerNotifications


# Plugin that stores APNS tokens reported from Android devices to know which Android devices to alert
# when print is done or other relevant events

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
		self._job_notifications = JobNotifications(self._logger)
		self._tool_notifications = ToolsNotifications(self._logger)
		self._bed_notifications = BedNotifications(self._logger)
		self._mmu_assitance = MMUAssistance(self._logger)
		self._paused_for_user = PausedForUser(self._logger)
		self._palette2 = Palette2Notifications(self._logger)
		self._layerNotifications = LayerNotifications(self._logger)

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

	# SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			debug_logging=False,
			server_url='https://fcm.googleapis.com/fcm/send',
			camera_snapshot_url='http://localhost:8080/?action=snapshot',
			tokens=[],
			temp_interval=5,
			tool0_low=0,
			bed_low=30,
			bed_target_temp_hold=10,
			mmu_interval=5,
			pause_interval=5,
			palette2_printing_error_codes=[103, 104, 111, 121],
			progress_type='50'      # 0=disabled, 25=every 25%, 50=every 50%, 100=only when finished
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
		return 8

	def on_settings_migrate(self, target, current):
		if current == 1:
			# add the 2 new values included
			self._settings.set(['temp_interval'], self.get_settings_defaults()["temp_interval"])
			self._settings.set(['bed_low'], self.get_settings_defaults()["bed_low"])

		if current <= 2:
			self._settings.set(['bed_target_temp_hold'], self.get_settings_defaults()["bed_target_temp_hold"])

		if current <= 3:
			self._settings.set(['mmu_interval'], self.get_settings_defaults()["mmu_interval"])

		if current <= 4:
			self._settings.set(['pause_interval'], self.get_settings_defaults()["pause_interval"])

		if current <= 5:
			self._settings.set(['tool0_low'], self.get_settings_defaults()["tool0_low"])

		if current <= 6:
			self._settings.set(['palette2_printing_error_codes'],
							   self.get_settings_defaults()["palette2_printing_error_codes"])

		if current <= 7:
			self._settings.set(['progress_type'],
							   self.get_settings_defaults()["progress_type"])

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
		self._job_notifications.on_print_progress(self._settings, progress)

	# EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == Events.PRINTER_STATE_CHANGED:
			self._job_notifications.send__print_job_notification(self._settings, self._printer, payload)
		elif event == "DisplayLayerProgress_layerChanged":
			# Event sent from DisplayLayerProgress plugin when there was a detected layer changed
			self._layerNotifications.layer_changed(self._settings, payload["currentLayer"])
		elif event == Events.PRINT_STARTED or event == Events.PRINT_DONE or event == Events.PRINT_CANCELLED \
				or event == Events.PRINT_FAILED:
			# Reset layers for which we need to send a notification. Each new print job has its own
			self._layerNotifications.reset_layers()

	# SimpleApiPlugin mixin

	def update_token(self, old_token, new_token, device_name, printer_id, printer_name, language_code):
		self._logger.debug("Received tokens for %s." % device_name)

		existing_tokens = self._settings.get(["tokens"])

		# Safety check in case a user manually modified config.yaml and left invalid JSON
		if existing_tokens is None:
			existing_tokens = []

		found = False
		updated = False
		for token in existing_tokens:
			# Check if existing token has been updated
			if token["apnsToken"] == old_token and token["printerID"] == printer_id:
				if old_token != new_token:
					self._logger.debug("Updating token for %s." % device_name)
					# Token that exists needs to be updated with new token
					token["apnsToken"] = new_token
					token["date"] = datetime.datetime.now()
					updated = True
				found = True
			elif token["apnsToken"] == new_token and token["printerID"] == printer_id:
				found = True

			if found:
				if printer_name is not None and ("printerName" not in token or token["printerName"] != printer_name):
					# Printer name in Printoid has been updated
					token["printerName"] = printer_name
					token["date"] = datetime.datetime.now()
					updated = True
				if language_code is not None and ("languageCode" not in token or token["languageCode"] != language_code):
					# Language being used by Printoid has been updated
					token["languageCode"] = language_code
					token["date"] = datetime.datetime.now()
					updated = True
				break

		if not found:
			self._logger.debug("Adding token for %s." % device_name)
			# Token was not found so we need to add it
			existing_tokens.append({'apnsToken': new_token, 'deviceName': device_name, 'date': datetime.datetime.now(),
									'printerID': printer_id, 'printerName': printer_name, 'languageCode': language_code})
			updated = True
		if updated:
			# Save new settings
			self._settings.set(["tokens"], existing_tokens)
			self._settings.save()
			eventManager().fire(Events.SETTINGS_UPDATED)
			self._logger.debug("Tokens saved")

	def get_api_commands(self):
		return dict(updateToken=["oldToken", "newToken", "deviceName", "printerID"], test=[],
					snooze=["eventCode", "minutes"], addLayer=["layer"], removeLayer=["layer"], getLayers=[])

	def on_api_command(self, command, data):
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == 'updateToken':
			# Convert from ASCII to UTF-8 since somce chars will fail otherwise
			data["deviceName"] = data["deviceName"].encode("utf-8")
			printer_name = data["printerName"] if 'printerName' in data else None
			language_code = data["languageCode"] if 'languageCode' in data else None

			self.update_token("{oldToken}".format(**data), "{newToken}".format(**data), "{deviceName}".format(**data),
							  "{printerID}".format(**data), printer_name, language_code)
		elif command == 'test':
			payload = dict(
				state_id="OPERATIONAL",
				state_string="Operational"
			)
			code = self._job_notifications.send__print_job_notification(self._settings, self._printer, payload,
																		data["server_url"], data["camera_snapshot_url"],
																		True)
			return flask.jsonify(dict(code=code))
		elif command == 'snooze':
			if data["eventCode"] == 'mmu-event':
				self._mmu_assitance.snooze(data["minutes"])
			else:
				return flask.make_response("Snooze for unknown event", 400)
		elif command == 'addLayer':
			self._layerNotifications.add_layer(data["layer"])
		elif command == 'removeLayer':
			self._layerNotifications.remove_layer(data["layer"])
		elif command == 'getLayers':
			return flask.jsonify(dict(layers=self._layerNotifications.get_layers()))
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

	# GCODE hook

	def process_gcode(self, comm, line, *args, **kwargs):
		line = self._paused_for_user.process_gcode(self._settings, self._printer, line)
		return self._mmu_assitance.process_gcode(self._settings, line)


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
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.process_gcode
	}

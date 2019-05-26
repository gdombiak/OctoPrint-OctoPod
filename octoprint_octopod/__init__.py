# coding=utf-8
from __future__ import absolute_import

from octoprint.server import user_permission
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer
from PIL import Image
import logging
import flask
import requests, StringIO
import datetime
import json
import time

# Plugin that stores APNS tokens reported from iOS devices to know which iOS devices to alert
# when print is done or other relevant events

import octoprint.plugin

class OctopodPlugin(octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.AssetPlugin,
                    octoprint.plugin.TemplatePlugin,
					octoprint.plugin.StartupPlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.EventHandlerPlugin):

	_lastPrinterState = None

	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.octopod")
		self._checkTempTimer = None
		self._printer_was_printing_above_bed_low = False # Variable used for bed cooling alerts
		self._printer_not_printing_reached_target_temp_start_time = None # Variable used for bed warming alerts

	##~~ StartupPlugin mixin

	def on_after_startup(self):
		self._logger.info("OctoPod loaded!")
		# Start timer that will check bed temperature and send notifications if needed
		self._restartTimer()

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			debug_logging = False,
			server_url = 'http://octopodprint.com/',
			camera_snapshot_url = 'http://localhost:8080/?action=snapshot',
			api_key = None,
			tokens = [],
			temp_interval=5,
			bed_low=30,
			bed_target_temp_hold=10
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
		return 3

	def on_settings_migrate(self, target, current):
		if current == 1:
			# add the 2 new values included
			self._settings.set(['temp_interval'], self.get_settings_defaults()["temp_interval"])
			self._settings.set(['bed_low'], self.get_settings_defaults()["bed_low"])

		if current <= 2:
			self._settings.set(['bed_target_temp_hold'], self.get_settings_defaults()["bed_target_temp_hold"])

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/octopod.js"],
			css=["css/octopod.css"],
		)

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == Events.PRINTER_STATE_CHANGED:
			self.send__print_job_notification()

	##~~ SimpleApiPlugin mixin

	def updateToken(self, oldToken, newToken, deviceName, printerID):
		self._logger.debug("Received tokens for %s." % deviceName)

		existing_tokens = self._settings.get(["tokens"])

		## Safety check in case a user manually modified config.yaml and left invalid JSON
		if existing_tokens == None:
			existing_tokens = []

		found = False
		updated = False
		for token in existing_tokens:
			# Check if existing token has been updated
			if token["apnsToken"] == oldToken and token["printerID"] == printerID:
				if oldToken != newToken:
					self._logger.debug("Updating token for %s." % deviceName)
					# Token that exists needs to be updated with new token
					token["apnsToken"] = newToken
					token["date"] = datetime.datetime.now()
					updated = True
				found = True
				break
		if not found:
			self._logger.debug("Adding token for %s." % deviceName)
			# Token was not found so we need to add it
			existing_tokens.append({'apnsToken': newToken, 'deviceName': deviceName, 'date': datetime.datetime.now(), 'printerID': printerID})
			updated = True
		if updated:
			# Save new settings
			self._settings.set(["tokens"], existing_tokens)
			self._settings.save()
			eventManager().fire(Events.SETTINGS_UPDATED)
			self._logger.debug("Tokens saved")

	def get_api_commands(self):
		return dict(updateToken=["oldToken", "newToken", "deviceName", "printerID"], test=[])

	def on_api_command(self, command, data):
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == 'updateToken':
			# Convert from ASCII to UTF-8 since somce chars will fail otherwise
			data["deviceName"] = data["deviceName"].encode("utf-8")
			self.updateToken("{oldToken}".format(**data), "{newToken}".format(**data), "{deviceName}".format(**data), "{printerID}".format(**data))
		elif command == 'test':
			code = self.send__print_job_notification(data["server_url"], data["camera_snapshot_url"], True)
			return flask.jsonify(dict(code=code))


	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", name="OctoPod Notifications", custom_bindings=True)
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			octopod=dict(
				displayName="OctoPod Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="gdombiak",
				repo="OctoPrint-OctoPod",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/gdombiak/OctoPrint-OctoPod/archive/{target_version}.zip"
			)
		)

	##~~ Temp Timer functions

	def _restartTimer(self):
		# stop the timer
		if self._checkTempTimer:
			self._logger.debug(u"Stopping Timer...")
			self._checkTempTimer.cancel()
			self._checkTempTimer = None

		# start a new timer
		interval = self._settings.get_int(['temp_interval'])
		if interval:
			self._logger.debug(u"Starting Timer...")
			self._checkTempTimer = RepeatedTimer(interval, self.CheckTemps, None, None, True)
			self._checkTempTimer.start()

	def CheckTemps(self):
		temps = self._printer.get_current_temperatures()
		self._logger.debug(u"CheckTemps(): %r" % (temps,))
		if not temps:
			self._logger.debug(u"No Temperature Data")
			return

		for k in temps.keys():
			# example dictionary from octoprint
			# {
			#   'bed': {'actual': 0.9, 'target': 0.0, 'offset': 0},
			#   'tool0': {'actual': 0.0, 'target': 0.0, 'offset': 0},
			#   'tool1': {'actual': 0.0, 'target': 0.0, 'offset': 0}
			# }
			if k == 'bed':
				threshold_low = self._settings.get_int(['bed_low'])
				target_temp_minutes_hold = self._settings.get_int(['bed_target_temp_hold'])
			else:
				continue

			# Check if bed has cooled down to specified temperature once print is finished
			# Remember if we are printing and current bed temp is above the low bed threshold
			if not self._printer_was_printing_above_bed_low and self._printer.is_printing() and threshold_low and temps[k]['actual'] > threshold_low:
				self._printer_was_printing_above_bed_low = True

			# If we are not printing and we were printing before with bed temp above bed threshold and bed temp is now below bed threshold
			if self._printer_was_printing_above_bed_low and not self._printer.is_printing() and threshold_low and temps[k]['actual'] < threshold_low:
				self._logger.debug("Print done and bed temp is now below threshold {0}. Actual {1}.".format(threshold_low, temps[k]['actual']))
				self._printer_was_printing_above_bed_low = False

				self.send__bed_notification("bed-cooled", threshold_low, None)



			# Check if bed has warmed to target temperature for the desired time before print starts
			if temps[k]['target'] > 0:
				bed_fluctuation = 1   # Temperatures fluctuate so accept this margin of error
				# Mark time when bed reached target temp
				if not self._printer_not_printing_reached_target_temp_start_time and not self._printer.is_printing() and temps[k]['actual'] > (temps[k]['target'] - bed_fluctuation):
					self._printer_not_printing_reached_target_temp_start_time = time.time()

				# Reset time if printing or bed is below target temp and we were tracking time
				if self._printer.is_printing() or (self._printer_not_printing_reached_target_temp_start_time and temps[k]['actual'] < (temps[k]['target'] - bed_fluctuation)):
					self._printer_not_printing_reached_target_temp_start_time = None

				if target_temp_minutes_hold and self._printer_not_printing_reached_target_temp_start_time:
					warmed_time_seconds = time.time() - self._printer_not_printing_reached_target_temp_start_time
					warmed_time_minutes = warmed_time_seconds / 60
					if warmed_time_minutes > target_temp_minutes_hold:
						self._logger.debug("Bed reached target temp for {0} minutes".format(warmed_time_minutes))
						self._printer_not_printing_reached_target_temp_start_time = None

						self.send__bed_notification("bed-warmed", temps[k]['target'], int(warmed_time_minutes))

	##~~ Private functions - Print Job Notifications

	def send__print_job_notification(self, server_url = None, camera_snapshot_url = None, test = False):
		if server_url:
			url = server_url
		else:
			url = self._settings.get(["server_url"])
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = self._settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		url = url + '/v1/push_printer'

		# Gather information about progress completion of the job
		completion = None
		current_data = self._printer.get_current_data()
		if "progress" in current_data and current_data["progress"] is not None \
				and "completion" in current_data["progress"] and current_data["progress"][
			"completion"] is not None:
			completion = current_data["progress"]["completion"]

		current_printer_state_id = self._printer.get_state_id()
		if not test:
			# Ignore other states that are not any of the following
			if current_printer_state_id != "OPERATIONAL" and current_printer_state_id != "PRINTING" and \
				current_printer_state_id != "PAUSED" and current_printer_state_id != "CLOSED" and \
				current_printer_state_id != "ERROR" and current_printer_state_id != "CLOSED_WITH_ERROR" and \
				current_printer_state_id != "OFFLINE":
				return -3

			current_printer_state = self._printer.get_state_string()
			if current_printer_state == self._lastPrinterState:
				# OctoPrint may report the same state more than once so ignore dups
				return -4

			self._lastPrinterState = current_printer_state
		else:
			current_printer_state_id = "OPERATIONAL"
			current_printer_state = "Operational"
			completion = 100

		# Get a snapshot of the camera
		image = None
		if completion == 100 and current_printer_state_id == "OPERATIONAL":
			# Only include image when print is complete. This is an optimization to avoid sending
			# images that won't be rendered by the app
			try:
				if camera_snapshot_url:
					camera_url = camera_snapshot_url
				else:
					camera_url = self._settings.get(["camera_snapshot_url"])
				if camera_url and camera_url.strip():
					image = self.image()
			except:
				self._logger.info("Could not load image from url")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		usedTokens = []
		last_result = None
		for token in tokens:
			apnsToken = token["apnsToken"]
			printerID = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the iOS app. Usually one for local address and one for public address
			if apnsToken in usedTokens:
				continue
			# Keep track of tokens that received a notification
			usedTokens.append(apnsToken)

			last_result = self.send_job_request(apnsToken, image, printerID, current_printer_state, completion, url, test)

		return last_result


	def send_job_request(self, apnsToken, image, printerID, printerState, completion, url, test = False):
		data = {"tokens": [apnsToken], "printerID": printerID, "printerState": printerState, "silent": True}

		if completion:
			data["printerCompletion"] = completion

		if test:
			data["test"] = True

		try:
			if image:
				files = {}
				files['image'] = ("image.jpg", image, "image/jpeg")
				files['json'] = (None, json.dumps(data), "application/json")

				r = requests.post(url, files=files)
			else:
				r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Print Job Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Print Job Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send message: %s" % str(e))
			return -500

	def image(self):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		snapshot_url = self._settings.get(["camera_snapshot_url"])
		if not snapshot_url:
			return None

		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True).content

		hflip = self._settings.global_get(["webcam", "flipH"])
		vflip = self._settings.global_get(["webcam", "flipV"])
		rotate = self._settings.global_get(["webcam", "rotate90"])

		if hflip or vflip or rotate:
			# https://www.blog.pythonlibrary.org/2017/10/05/how-to-rotate-mirror-photos-with-python/
			image_obj = Image.open(StringIO.StringIO(image))
			if hflip:
				image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
			if vflip:
				image_obj = image_obj.transpose(Image.FLIP_TOP_BOTTOM)
			if rotate:
				image_obj = image_obj.rotate(90)

			# https://stackoverflow.com/questions/646286/python-pil-how-to-write-png-image-to-string/5504072
			output = StringIO.StringIO()
			image_obj.save(output, format="JPEG")
			image = output.getvalue()
			output.close()
		return image

	##~~ Private functions - Bed Notifications

	def send__bed_notification(self, event_code, temperature, minutes):
		url = self._settings.get(["server_url"])
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = self._settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		url = url + '/v1/push_printer/bed_events'

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		usedTokens = []
		last_result = None
		for token in tokens:
			apnsToken = token["apnsToken"]
			printerID = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the iOS app. Usually one for local address and one for public address
			if apnsToken in usedTokens:
				continue
			# Keep track of tokens that received a notification
			usedTokens.append(apnsToken)

			last_result = self.send_bed_request(url, apnsToken, printerID, event_code, temperature, minutes)

		return last_result

	def send_bed_request(self, url, apnsToken, printerID, event_code, temperature, minutes):
		data = {"tokens": [apnsToken], "printerID": printerID, "eventCode": event_code, "temperature": temperature,
				"silent": True}

		if minutes:
			data["minutes"] = minutes

		try:
			r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Bed Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Bed Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send Bed Notification: %s" % str(e))
			return -500


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "OctoPod Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctopodPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}


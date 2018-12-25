# coding=utf-8
from __future__ import absolute_import

from octoprint.server import user_permission
from octoprint.events import eventManager, Events
from PIL import Image
import logging
import flask
import requests, StringIO
import datetime
import json

# Plugin that stores APNS tokens reported from iOS devices to know which iOS devices to alert
# when print is done or other relevant events

import octoprint.plugin

class OctopodPlugin(octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.AssetPlugin,
                    octoprint.plugin.TemplatePlugin,
					octoprint.plugin.StartupPlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.EventHandlerPlugin):

	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.octopod")
		self._octopod_logger = logging.getLogger("octoprint.plugins.octopod.debug")

	##~~ StartupPlugin mixin

	def on_startup(self, host, port):
		# setup customized logger
		from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
		octopod_logging_handler = CleaningTimedRotatingFileHandler(
			self._settings.get_plugin_logfile_path(postfix="debug"), when="D", backupCount=3)
		octopod_logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
		octopod_logging_handler.setLevel(logging.DEBUG)

		self._octopod_logger.addHandler(octopod_logging_handler)
		self._octopod_logger.setLevel(
			logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.INFO)
		self._octopod_logger.propagate = False

	def on_after_startup(self):
		self._logger.info("OctoPod loaded!")

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			debug_logging = False,
			server_url = '',
			camera_snapshot_url = 'http://localhost:8080/?action=snapshot',
			api_key = None,
			tokens = []
		)

	def on_settings_save(self, data):
		old_debug_logging = self._settings.get_boolean(["debug_logging"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_debug_logging = self._settings.get_boolean(["debug_logging"])
		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._octopod_logger.setLevel(logging.DEBUG)
			else:
				self._octopod_logger.setLevel(logging.INFO)

	def get_settings_version(self):
		return 1

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
		if event == Events.PRINT_DONE:
			self.send_notification("Print Complete")
		elif event == Events.PRINT_FAILED:
			self.send_notification("Pring Failed")

	##~~ SimpleApiPlugin mixin

	def updateToken(self, oldToken, newToken, deviceName):
		self._octopod_logger.debug("Received tokens for %s." % deviceName)

		existing_tokens = self._settings.get(["tokens"])
		found = False
		updated = False
		for token in existing_tokens:
			# Check if existing token has been updated
			if token["apnsToken"] == oldToken:
				if oldToken != newToken:
					self._octopod_logger.debug("Updating token for %s." % deviceName)
					# Token that exists needs to be updated with new token
					token["apnsToken"] = newToken
					token["date"] = datetime.datetime.now()
					updated = True
				found = True
				break
		if not found:
			self._octopod_logger.debug("Adding token for %s." % deviceName)
			# Token was not found so we need to add it
			existing_tokens.append({'apnsToken': newToken,'deviceName': deviceName,'date': datetime.datetime.now()})
			updated = True
		if updated:
			# Save new settings
			self._settings.set(["tokens"], existing_tokens)
			self._settings.save()
			eventManager().fire(Events.SETTINGS_UPDATED)
			self._octopod_logger.debug("Tokens saved")

	def get_api_commands(self):
		return dict(updateToken=["oldToken", "newToken", "deviceName"], test=[])

	def on_api_command(self, command, data):
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == 'updateToken':
			self.updateToken("{oldToken}".format(**data), "{newToken}".format(**data), "{deviceName}".format(**data))
		elif command == 'test':
			code = self.send_notification("Testing push notification", data["server_url"], data["camera_snapshot_url"])
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

	##~~ Private functions

	def send_notification(self, message, server_url, camera_snapshot_url):
		# Create an url, if the fqdn is not correct you can manually set it at your config.yaml
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
			return -1

		apnsTokens = []
		for token in tokens:
			apnsTokens.append(token["apnsToken"])

		if self._printer_profile_manager is not None and "name" in self._printer_profile_manager.get_current_or_default():
			message = "%s - %s" % (self._printer_profile_manager.get_current_or_default()["name"], message)

		data = {"appId": "org.octopod", "tokens": apnsTokens, "message": message}
		files = {}
		try:
			if camera_snapshot_url:
				camera_url = camera_snapshot_url
			else:
				camera_url = self._settings.get(["camera_snapshot_url"])
			if camera_url and camera_url.strip():
				files['image'] = ("image.jpg", self.image(), "image/jpeg")
				files['json'] = (None, json.dumps(data), "application/json")
		except:
			self._logger.info("Could not load image from url")

		# Multiple try catches so it will always send a message if the image raises an Exception
		try:
			if len(files) > 0:
				r = requests.post(url, files=files)
			else:
				r = requests.post(url, json=data)
			if r.status_code >= 400:
				self._logger.info("Response: %s" % str(r.content))
			else:
				self._logger.debug("Response: %s" % str(r.content))
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


from io import BytesIO  ## for Python 2 & 3

import requests
import time
from PIL import Image

from .alerts import Alerts


class BaseNotification:
	_plugin_manager = None

	def __init__(self, logger, plugin_manager):
		self._logger = logger
		self._alerts = Alerts(self._logger)
		self._plugin_manager = plugin_manager

	def image(self, turn_on_ifneeded, snapshot_url, hflip, vflip, rotate):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = self.__take_image_snapshot(snapshot_url)

		try:
			image_obj = Image.open(BytesIO(image))

			# if octolight HA plugin is installed then check if room is dark and turn on the light if needed
			octolightHA = self._plugin_manager.plugins.get("octolightHA")
			if octolightHA is not None and octolightHA.enabled and turn_on_ifneeded:
				if self.__is_image_dark(image_obj):
					# Some webcams need a sec to adapt to lighting conditions. They initially see black. Wait a sec
					time.sleep(1)
					# Fetch another snapshot
					image = self.__take_image_snapshot(snapshot_url)
					image_obj = Image.open(BytesIO(image))
					# Check again if still dark
					if self.__is_image_dark(image_obj):
						self._logger.debug("Toggling HA light")
						# Turn on the light
						octolightHA.implementation.toggle_HA_state()
						# Add a delay of 1 second to wait for HA to turn on the light and camera tune to new luminance
						time.sleep(1)
						# Fetch image again
						image = self.__take_image_snapshot(snapshot_url)
						image_obj = Image.open(BytesIO(image))
						# Turn on the light
						octolightHA.implementation.toggle_HA_state()

			# Reduce resolution of image to prevent 400 error when uploading content
			# Besides this saves network bandwidth and iOS device or Apple Watch
			# cannot tell the difference in resolution
			x, y = image_obj.size
			if x > 1640 or y > 1232:
				size = 1640, 1232
				# ANTIALIAS was removed in Pillow 10.0.0 so check which variation we can use
				image_obj.thumbnail(size, Image.ANTIALIAS if hasattr(Image, "ANTIALIAS") else Image.Resampling.LANCZOS)
				# image_obj.thumbnail(size, Image.ANTIALIAS)
				output = BytesIO()
				image_obj.save(output, format="JPEG")
				image = output.getvalue()
				output.close()
		except Exception as e:
			self._logger.debug("Error reducing resolution of image: %s" % str(e))

		if hflip or vflip or rotate:
			try:
				# https://www.blog.pythonlibrary.org/2017/10/05/how-to-rotate-mirror-photos-with-python/
				image_obj = Image.open(BytesIO(image))
				if hflip:
					image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
				if vflip:
					image_obj = image_obj.transpose(Image.FLIP_TOP_BOTTOM)
				if rotate:
					image_obj = image_obj.rotate(90)

				# https://stackoverflow.com/questions/646286/python-pil-how-to-write-png-image-to-string/5504072
				output = BytesIO()
				image_obj.save(output, format="JPEG")
				image = output.getvalue()
				output.close()
			except Exception as e:
				self._logger.debug("Error rotating image: %s" % str(e))

		return image

	def __take_image_snapshot(self, snapshot_url):
		return requests.get(snapshot_url, stream=True, timeout=(4, 10)).content

	def __is_image_dark(self, image_obj):
		# Check image luminance to detect if it's dark and we need to
		# turn on the Home Assistant Light (if plugin is installed)
		# Get the pixel values as a numpy array
		pixels = list(image_obj.getdata())

		# Calculate the total luminance of all pixels
		lum_sum = 0
		for pixel in pixels:
			r, g, b = pixel
			# Use perceived luminance formula
			lum = (r * 0.299) + (g * 0.587) + (b * 0.114)
			lum_sum += lum

		# Get the average luminance
		avg_lum = lum_sum / len(pixels)
		# Luminance below threshold is considered a dark image. Use same value used in iOS app
		threshold = 40
		if avg_lum < threshold:
			self._logger.debug("Camera image seems to have low light. Luminance: %s" % str(avg_lum))
			return True
		return False

	def _send_base_notification(self, settings, include_image, event_code, category=None, event_param=None,
								apns_dict=None, silent_code_block=None, legacy_code_block=None):
		"""
		Send push notification for a specific code to OctoPod app running on iPhone (includes Apple Watch and iPad)
		via the OctoPod APNS service. Message to send is based on requested code and iPhone's language

		:param settings: Plugin settings
		:param include_image: Flag to indicate if snapshot of camera should be included
		:param event_code: Code representing the message to send
		:param category: Optional. Category supported by OctoPod app. Actions depend on the category
		:param event_param: Optional. Replace {} in the message with specified parameters
		:param apns_dict: Optional. Extra information to include in the notification. Useful for actions.
		:param silent_code_block: Optional. Code to execute after push notification was sent. Useful for silent
		notifications
		:param legacy_code_block: Optional.If using legacy notifications (should be deprecated by now) then execute
		this code
		:return: Negative value if failed to send notification or otherwise HTTP status code returned
		by OctoPod APNS service (see url param)
		"""
		server_url = self._get_server_url(settings)
		if not server_url or not server_url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		url = server_url + '/v1/push_printer'

		# Get a snapshot of the camera
		image = None
		if include_image:
			try:
				hflip = settings.get(["webcam_flipH"])
				vflip = settings.get(["webcam_flipV"])
				rotate = settings.get(["webcam_rotate90"])
				camera_url = settings.get(["camera_snapshot_url"])
				turn_on_ifneeded = settings.get_boolean(['turn_HA_light_on_ifneeded'])
				if camera_url and camera_url.strip():
					image = self.image(turn_on_ifneeded, camera_url, hflip, vflip, rotate)
			except:
				self._logger.info("Could not load image from url")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			apns_token = token["apnsToken"]
			printer_id = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the iOS app. Usually one for local address and one for public address
			if apns_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(apns_token)

			if 'printerName' in token and token["printerName"] is not None:
				# We can send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				language_code = token["languageCode"]
				last_result = self._alerts.send_alert_code(settings, language_code, apns_token, url, printer_name,
														   event_code, category, image, event_param, apns_dict)
			else:
				# Legacy mode that uses silent notifications. As user update OctoPod app then they will automatically
				# switch to the new mode
				if legacy_code_block:
					last_result = legacy_code_block(server_url, apns_token, printer_id)

			if silent_code_block:
				# Send silent notification to refresh Apple Watch complication
				silent_code_block(apns_token, image, printer_id, url)

		return last_result

	def _send_arbitrary_notification(self, settings, message, image):
		"""
		Send arbitrary push notification to OctoPod app running on iPhone (includes Apple Watch and iPad)
		via the OctoPod APNS service.

		:param settings: Plugin settings
		:param message: Message to include in the notification
		:param image: Optional. Image to include in the notification
		:return: True if the notification was successfully sent
		"""
		server_url = self._get_server_url(settings)
		if not server_url or not server_url.strip():
			# No APNS server has been defined so do nothing
			self._logger.debug("CustomNotifications - No APNS server has been defined so do nothing")
			return False

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			self._logger.debug("CustomNotifications - No iOS devices were registered so skip notification")
			return False

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			apns_token = token["apnsToken"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the iOS app. Usually one for local address and one for public address
			if apns_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(apns_token)

			if 'printerName' in token and token["printerName"] is not None:
				# We can send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				url = server_url + '/v1/push_printer'

				return self._alerts.send_alert(settings, apns_token, url, printer_name, message, None, image) < 300

	def _is_printer_printing(self, printer):
		(completion, print_time_in_seconds, print_time_left_in_seconds) = self._get_progress_data(printer)
		# Check that we are in the middle of a print
		return not(completion is None or completion == 0 or completion == 100)

	def _get_progress_data(self, printer, reported_progress=None):
		completion = None if reported_progress is None else reported_progress
		print_time_in_seconds = None
		print_time_left_in_seconds = None
		current_data = printer.get_current_data()
		if "progress" in current_data and current_data["progress"] is not None \
				and "completion" in current_data["progress"] and current_data["progress"][
			"completion"] is not None:
			print_time_left_in_seconds = current_data["progress"]["printTimeLeft"]
			print_time_in_seconds = current_data["progress"]["printTime"]
			completion = current_data["progress"]["completion"] if reported_progress is None else reported_progress
			# Ugly hack - PrintTimeGenius changed reported completion so we need to use their conversion function
			completion = self._convert_progress(completion, print_time_in_seconds, print_time_left_in_seconds)
		return completion, print_time_in_seconds, print_time_left_in_seconds


	@staticmethod
	def _get_server_url(settings):
		server_url = settings.get(["server_url"])
		if server_url:
			# Remove any beginning or trailing spaces
			server_url = server_url.strip()
			# Remove trailing / if there is one
			if server_url.endswith('/'):
				server_url = server_url[:-1]
		return server_url

	def _convert_progress(self, progress, print_time, time_left):
		"""
		PrintTimeGenius plugin changed the way progress is calculated. If this plugin is installed then the reported
		progress by OctoPrint might be wrong and hence needs to be calculated based on printing time.
		"""
		if print_time is None or time_left is None:
			return progress
		# Check if PrintTimeGenius plugin is installed and enabled
		print_time_genius_plugin = self._plugin_manager.plugins.get("PrintTimeGenius")
		if print_time_genius_plugin is not None and print_time_genius_plugin.enabled and time_left > 0:
			return print_time / (print_time + time_left) * 100
		return progress


from io import BytesIO  ## for Python 2 & 3

import requests
from PIL import Image

from .alerts import Alerts


class BaseNotification:

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)

	def image(self, snapshot_url, hflip, vflip, rotate):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True, timeout=(4, 10)).content

		try:
			# Reduce resolution of image to prevent 400 error when uploading content
			# Besides this saves network bandwidth and iOS device or Apple Watch
			# cannot tell the difference in resolution
			image_obj = Image.open(BytesIO(image))
			x, y = image_obj.size
			if x > 1640 or y > 1232:
				size = 1640, 1232
				image_obj.thumbnail(size, Image.ANTIALIAS)
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

	def _send_base_notification(self, settings, include_image, event_code, category=None, event_param=None,
								apns_dict=None, silent_code_block=None, legacy_code_block=None):
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
				if camera_url and camera_url.strip():
					image = self.image(camera_url, hflip, vflip, rotate)
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

from io import BytesIO ## for Python 2 & 3

import requests
from PIL import Image

from .alerts import Alerts


class TestNotifications:

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)

	def send__test(self, settings, testMessage):
		url = settings.get(["server_url"])
		if not url or not url.strip():
			# No FCM server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			return -2

		# Get a snapshot of the camera
		image = None
		try:
			camera_url = settings.get(["camera_snapshot_url"])
			if camera_url and camera_url.strip():
				image = self.image(settings)
		except:
			self._logger.info("Could not load image from url")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# Android app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			fcm_token = token["fcmToken"]
			printer_id = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the Android app. Usually one for local address and one for public address
			if fcm_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(fcm_token)

			if 'printerName' in token and token["printerName"] is not None:
				# We can send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				language_code = token["languageCode"]
				last_result = self._alerts.send_alert_code(language_code, fcm_token, url, printer_name,
														   testMessage, None, image)

		return last_result

	# Private functions - Test Notifications

	def image(self, settings):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		snapshot_url = settings.get(["camera_snapshot_url"])
		if not snapshot_url:
			return None

		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True).content

		hflip = settings.global_get(["webcam", "flipH"])
		vflip = settings.global_get(["webcam", "flipV"])
		rotate = settings.global_get(["webcam", "rotate90"])

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
				self._logger.debug( "Error rotating image: %s" % str(e) )

		return image

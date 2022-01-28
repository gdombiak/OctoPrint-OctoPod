from .base_notification import BaseNotification


class CustomNotifications(BaseNotification):
	"""
	Class only used for sending free form push notifications to the phone. This is
	only used as a service offered by this plugin to other plugins interested in
	sending arbitrary notifications to Printoid app.
	"""

	def __init__(self, logger):
		BaseNotification.__init__(self, logger)

	def send_notification(self, settings, message, image):
		"""
		Send arbitrary push notification to Printoid app running on Android
		via the Printoid FCM service.

		:param settings: Plugin settings
		:param message: Message to include in the notification
		:param image: Optional. Image to include in the notification
		:return: True if the notification was successfully sent
		"""
		server_url = self._get_server_url(settings)
		if not server_url or not server_url.strip():
			# No FCM server has been defined so do nothing
			self._logger.debug("CustomNotifications - No FCM server has been defined so do nothing")
			return False

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			self._logger.debug("CustomNotifications - No Android devices were registered so skip notification")
			return False

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# Android app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			fcm_token = token["fcmToken"]

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
				printer_id = token["printerId"]
				printer_name = token["printerName"]
				url = server_url

				return self._alerts.send_alert(settings, fcm_token, url, printer_id, printer_name, message, None, image) < 300

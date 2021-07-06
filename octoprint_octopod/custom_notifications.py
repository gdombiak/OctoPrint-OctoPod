from .alerts import Alerts
from PIL import Image


class CustomNotifications:
	"""
	Class only used for sending free form push notifications to the phone. This is
	only used as a service offered by this plugin to other plugins interested in
	sending arbitrary notifications to OctoPod app.
	"""

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)

	def send_notification(self, settings, message: str, image: Image) -> bool:
		"""
		Send arbitrary push notification to OctoPod app running on iPhone (includes Apple Watch and iPad)
		via the OctoPod APNS service.

		:param settings: Plugin settings
		:param message: Message to include in the notification
		:param image: Optional. Image to include in the notification
		:return: True if the notification was successfully sent
		"""
		server_url = settings.get(["server_url"])
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

				return self._alerts.send_alert(apns_token, url, printer_name, message, None, image) < 300

from .base_notification import BaseNotification

class TestNotifications(BaseNotification):

	def __init__(self, logger):
		BaseNotification.__init__(self, logger)
		self._logger = logger

	def send__test(self, settings):
		url = settings.get(["server_url"])
		if not url or not url.strip():
			# No FCM server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			return -2

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
				last_result= self._send_base_notification(settings,
														  include_image=True,
														  event_code="test-message")

		return last_result

	# Private functions - Test Notifications

from .base_notification import BaseNotification


class CustomNotifications(BaseNotification):
	"""
	Class only used for sending free form push notifications to the phone. This is
	only used as a service offered by this plugin to other plugins interested in
	sending arbitrary notifications to OctoPod app.
	"""

	def __init__(self, logger, plugin_manager):
		BaseNotification.__init__(self, logger, plugin_manager)

	def send_notification(self, settings, message, image):
		"""
		Send arbitrary push notification to OctoPod app running on iPhone (includes Apple Watch and iPad)
		via the OctoPod APNS service.

		:param settings: Plugin settings
		:param message: Message to include in the notification
		:param image: Optional. Image to include in the notification
		:return: True if the notification was successfully sent
		"""
		return self._send_arbitrary_notification(settings, message,image)

from .base_notification import BaseNotification


class Palette2Notifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts

	def check_plugin_message(self, settings, plugin, data):
		if plugin == "palette2" and 'command' in data and data["command"] == "error":
			# Only send notifications for error codes that may happen while printing
			p2_printing_error_codes = settings.get(["palette2_printing_error_codes"])
			error_code = data["data"]
			if error_code in p2_printing_error_codes:
				self._logger.info("*** P2/P encountered error {} while printing ***".format(error_code))
				self.__send_palette_notification(settings, "palette2-error-while-printing", error_code)

	# Private functions - Notifications

	def __send_palette_notification(self, settings, event_code, error_code):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "palette2-error", error_code)

		return self._send_base_notification(settings,
											include_image=False,
											event_code=event_code,
											event_param=error_code)

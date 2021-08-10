from .alerts import Alerts


class Palette2Notifications:

	def __init__(self, logger, ifttt_alerts):
		self._logger = logger
		self._ifttt_alerts = ifttt_alerts
		self._alerts = Alerts(self._logger)

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

		server_url = settings.get(["server_url"])
		if not server_url or not server_url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

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
				language_code = token["languageCode"]
				url = server_url + '/v1/push_printer'

				last_result = self._alerts.send_alert_code(settings, language_code, apns_token, url, printer_name,
														   event_code, event_param=error_code)

		return last_result

from .alerts import Alerts


class ToolsNotifications:

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)
		self._printer_was_printing_above_tool0_low = False  # Variable used for tool0 cooling alerts

	def check_temps(self, settings, printer):
		temps = printer.get_current_temperatures()
		# self._logger.debug(u"CheckTemps(): %r" % (temps,))
		if not temps:
			# self._logger.debug(u"No Temperature Data")
			return

		for k in temps.keys():
			# example dictionary from octoprint
			# {
			#   'bed': {'actual': 0.9, 'target': 0.0, 'offset': 0},
			#   'tool0': {'actual': 0.0, 'target': 0.0, 'offset': 0},
			#   'tool1': {'actual': 0.0, 'target': 0.0, 'offset': 0}
			# }
			if k == 'tool0':
				tool0_threshold_low = settings.get_int(['tool0_low'])
			else:
				continue

			# Check if tool0 has cooled down to specified temperature once print is finished
			# Remember if we are printing and current tool0 temp is above the low tool0 threshold
			if not self._printer_was_printing_above_tool0_low and printer.is_printing() and tool0_threshold_low and \
				temps[k]['actual'] > tool0_threshold_low:
				self._printer_was_printing_above_tool0_low = True

			# If we are not printing and we were printing before with tool0 temp above threshold and tool0 temp is now
			# below threshold
			if self._printer_was_printing_above_tool0_low and not printer.is_printing() and tool0_threshold_low \
				and temps[k]['actual'] < tool0_threshold_low:
				self._logger.debug(
					"Print done and tool0 temp is now below threshold {0}. Actual {1}.".format(tool0_threshold_low,
																							 temps[k]['actual']))
				self._printer_was_printing_above_tool0_low = False

				self.send__tool_notification(settings, "tool0-cooled", tool0_threshold_low)

	##~~ Private functions - Tool Notifications

	def send__tool_notification(self, settings, event_code, temperature):
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

				last_result = self._alerts.send_alert_code(language_code, apns_token, url, printer_name, event_code,
														   None, None)

		return last_result

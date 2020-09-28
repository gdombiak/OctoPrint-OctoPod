import time

from .alerts import Alerts


class PausedForUser:

	def __init__(self, logger, ifttt_alerts):
		self._logger = logger
		self._ifttt_alerts = ifttt_alerts
		self._alerts = Alerts(self._logger)
		self._last_notification = None  # Keep track of when was user alerted last time. Helps avoid spamming
		self._snooze_end_time = time.time()  # Track when snooze for events ends. Assume snooze already expired

	def process_gcode(self, settings, printer, line):
		# Firmware will print to terminal when printer has paused for user

		# if line.startswith("Not SD printing"):
		if line.startswith("echo:busy: paused for user"):
			# Check if this type of notification is disabled
			pause_interval = settings.get_int(['pause_interval'])
			if pause_interval == 0:
				return line

			# Gather information about progress completion of the job
			completion = None
			current_data = printer.get_current_data()
			if "progress" in current_data and current_data["progress"] is not None \
				and "completion" in current_data["progress"] and current_data["progress"][
				"completion"] is not None:
				completion = current_data["progress"]["completion"]

			# Check that we are in the middle of a print
			if completion is None or completion == 0 or completion == 100:
				return line

			# Check if we never alerted or 5 minutes have passed since last alert
			if self._last_notification is None or (time.time() - self._last_notification) / 60 > pause_interval:
				self._logger.info("*** Printer paused for user ***")
				# Record last time we sent notification
				self._last_notification = time.time()
				# Send APNS Notification only if interval is not zero (user requested to
				# shutdown this notification) and there is no active snooze for this type of events
				if time.time() > self._snooze_end_time:
					self.__send_notification(settings)

		# Always return what we parsed
		return line

	def snooze(self, minutes):
		"""Snooze Pause For User events for the specified number of minutes"""
		self._snooze_end_time = time.time() + (minutes * 60)

	# Private functions

	def __send_notification(self, settings):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "paused-for-user", "")

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
				# Send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				language_code = token["languageCode"]
				url = server_url + '/v1/push_printer'

				last_result = self._alerts.send_alert_code(language_code, apns_token, url, printer_name,
														   "paused-user-event", None, None)

		return last_result

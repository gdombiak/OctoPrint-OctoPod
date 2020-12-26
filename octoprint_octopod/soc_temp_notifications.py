from .alerts import Alerts
import time

class SocTempNotifications:

	def __init__(self, logger, ifttt_alerts, interval, debugMode):
		self._logger = logger
		self._ifttt_alerts = ifttt_alerts
		self._alerts = Alerts(self._logger)
		self._checks_per_minute = 60 / interval # number of times a check will be done per minute
		self.sbc = None
		self.send_plugin_message = None

		self._checks_between_alerts = self._checks_per_minute if debugMode else self._checks_per_minute * 60 * 2 # Alert every 2 hours
		self._checks_since_alert = -1 # -1 means an alert was not sent in the last 2 hours

		self._recorded_temps = []
		self._record_max_count = self._checks_per_minute * 60 # Track 1 hour of temperatures

	def get_soc_temps(self):
		""" Returns list of recorded SoC temperatures """
		return self._recorded_temps

	def check_soc_temp(self, settings):
		soc_temp_threshold = settings.get_int(['soc_temp_high'])
		if soc_temp_threshold == 0:
			# Do nothing if user requested to disable this check
			return

		temp = float(self.sbc.check_soc_temp())
		self._logger.debug("SoC Temp: {0}".format(temp))

		# Update recorded SoC temps
		int_time = int(time.time())
		self._recorded_temps.append(dict(time= int_time, temp= temp))
		if len(self._recorded_temps) >= self._record_max_count:
			# remove oldest recorded temp to keep array within limits
			self._recorded_temps.pop(0)
		# Send websockets data with updated recorded temp
		self.send_plugin_message(dict(time= int_time, temp= temp))

		# Check if we need to send an alert due to high temp
		if self._checks_since_alert > -1:
			# An alert has been sent so count that we did a check
			self._checks_since_alert = self._checks_since_alert + 1
			# If number of checks has gone above time to be silent then reset counter
			if self._checks_since_alert > self._checks_between_alerts:
				self._checks_since_alert = -1
		if temp > soc_temp_threshold:
			# If an alert was not sent in the last 2 hours
			if self._checks_since_alert == -1:
				self.__send__soc_temp_notification(settings, soc_temp_threshold)
				self._checks_since_alert = 0 # Start counting alerts since we sent this alert

	def __send__soc_temp_notification(self, settings, soc_temp_threshold):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "soc-temp-exceeded", soc_temp_threshold)

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
			printerID = token["printerID"]

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

				last_result = self._alerts.send_alert_code(language_code, apns_token, url, printer_name,
														   "soc_temp_exceeded", None, None, soc_temp_threshold)

		return last_result

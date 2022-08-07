import time

from .base_notification import BaseNotification


class SocTempNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts, interval, debugMode):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
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
				self.__send__soc_temp_notification(settings, soc_temp_threshold, temp)
				self._checks_since_alert = 0 # Start counting alerts since we sent this alert

	def __send__soc_temp_notification(self, settings, soc_temp_threshold, soc_current_temp):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "soc-temp-exceeded", soc_temp_threshold)
		event_param = {'SoCThreshold': soc_temp_threshold, 'SoCTemp': soc_current_temp}
		return self._send_base_notification(settings, False, "soc_temp_exceeded", event_param=event_param)

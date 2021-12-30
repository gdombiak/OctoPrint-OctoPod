import time

from .base_notification import BaseNotification


class PausedForUser(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
		self._last_notification = None  # Keep track of when was user alerted last time. Helps avoid spamming
		self._snooze_end_time = time.time()  # Track when snooze for events ends. Assume snooze already expired

	def process_gcode(self, settings, printer, line):
		# Firmware will print to terminal when printer has paused for user

		# if line.startswith("Not SD printing"):
		if line.startswith("echo:busy: paused for user") or line.startswith("// action:paused"):
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
				else:
					self._logger.debug("PausedForUser Notification skipped. Snoozing until {0}"
									   .format(time.ctime(self._snooze_end_time)))

		# Always return what we parsed
		return line

	def snooze(self, minutes):
		"""Snooze Pause For User events for the specified number of minutes"""
		self._snooze_end_time = time.time() + (minutes * 60)
		self._logger.debug("PausedForUser Notification snoozing until {0}".format(time.ctime(self._snooze_end_time)))

	# Private functions

	def __send_notification(self, settings):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "paused-for-user", "")

		return self._send_base_notification(settings, False, "paused-user-event")

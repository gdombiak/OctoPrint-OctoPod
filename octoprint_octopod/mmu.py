import time

from .base_notification import BaseNotification


class MMUAssistance(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
		self._mmu_lines_skipped = None
		self._last_notification = None  # Keep track of when was user alerted last time. Helps avoid spamming
		self._snooze_end_time = time.time()  # Track when snooze for mmu events ends. Assume snooze already expired

	def process_gcode(self, settings, line):
		# MMU user assistance detection
		# Firmware will use 2 different lines to indicate the there is an MMU issue
		# and user assistance is required. There could be other lines present in the
		# terminal between the 2 relevant lines

		# if line.startswith("Not SD printing"):
		if line.startswith("mmu_get_response - begin move: T-code"):
			self._mmu_lines_skipped = 0
		else:
			if self._mmu_lines_skipped is not None:
				if self._mmu_lines_skipped > 5:
					# We give up waiting for the second line to be detected. False alert.
					# Reset counter
					self._mmu_lines_skipped = None
				# elif line.startswith("wait"):
				elif line.startswith("mmu_get_response() returning: 0"):
					# Check if we never alerted or 5 minutes have passed since last alert
					mmu_interval = settings.get_int(['mmu_interval'])
					if self._last_notification is None or (time.time() - self._last_notification) / 60 > mmu_interval:
						self._logger.info("*** MMU Requires User Assistance ***")
						# Record last time we sent notification
						self._last_notification = time.time()
						# Send APNS Notification only if interval is not zero (user requested to
						# shutdown this notification) and there is no active snooze for MMU events
						if mmu_interval > 0 and time.time() > self._snooze_end_time:
							self.__send__mmu_notification(settings)
						else:
							self._logger.debug("MMU Notification skipped. Snoozing until {0}"
											   .format(time.ctime(self._snooze_end_time)))

				# Second line found, reset counter now
					self._mmu_lines_skipped = None
				else:
					self._mmu_lines_skipped += 1

		# Always return what we parsed
		return line

	def snooze(self, minutes):
		"""Snooze MMU events for the specified number of minutes"""
		self._snooze_end_time = time.time() + (minutes * 60)
		self._logger.debug("MMU Notification snoozing until {0}".format(time.ctime(self._snooze_end_time)))

	##~~ Private functions - MMU Notifications

	def __send__mmu_notification(self, settings):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "mmu-event", "")

		return self._send_base_notification(settings, False, "mmu-event", "mmuSnoozeActions",
											legacy_code_block=self._send_legacy_notification)

	def _send_legacy_notification(self, server_url, apns_token, printer_id):
		# Legacy mode that uses silent notifications. As user update OctoPod app then they will automatically
		# switch to the new mode
		url = server_url + '/v1/push_printer/code_events'

		return self._alerts.send_mmu_request(url, apns_token, printer_id)

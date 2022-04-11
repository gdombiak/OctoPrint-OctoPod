import time

from .base_notification import BaseNotification


class BedNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
		self._printer_was_printing_above_bed_low = False  # Variable used for bed cooling alerts
		self._printer_not_printing_reached_target_temp_start_time = None  # Variable used for bed warming alerts
		self._bed_warming_notification_was_sent = False # Variable used for preventing bed warming alerts from sending more than once
		self._previous_bed_target_temp = 0 # The current/previously saved bed target temperature which is used
		# to determine when to reset whether the notification has been sent or not yet

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
			if k == 'bed':
				threshold_low = settings.get_int(['bed_low'])
				target_temp_minutes_hold = settings.get_int(['bed_target_temp_hold'])
				bed_warm_notify_once = settings.get_boolean(['bed_warm_notify_once'])
			else:
				continue

			# Check if bed has cooled down to specified temperature once print is finished
			# Remember if we are printing and current bed temp is above the low bed threshold
			if not self._printer_was_printing_above_bed_low and printer.is_printing() and threshold_low and temps[k][
				'actual'] > threshold_low:
				self._printer_was_printing_above_bed_low = True

			# If we are not printing and we were printing before with bed temp above bed threshold and bed temp is now
			# below bed threshold
			if self._printer_was_printing_above_bed_low and not printer.is_printing() and threshold_low and temps[k][
				'actual'] < threshold_low:
				self._logger.debug(
					"Print done and bed temp is now below threshold {0}. Actual {1}.".format(threshold_low,
																							 temps[k]['actual']))
				self._printer_was_printing_above_bed_low = False

				self.__send__bed_notification(settings, "bed-cooled", threshold_low, None)

			# Check if bed has warmed to target temperature for the desired time before print starts
			if temps[k]['target'] > 0:
				bed_fluctuation = 1  # Temperatures fluctuate so accept this margin of error
				# Mark time when bed reached target temp
				if not self._printer_not_printing_reached_target_temp_start_time and not printer.is_printing() and \
					temps[k]['actual'] > (temps[k]['target'] - bed_fluctuation):
					self._printer_not_printing_reached_target_temp_start_time = time.time()

				# Reset time if printing or bed is below target temp and we were tracking time
				if printer.is_printing() or (
					self._printer_not_printing_reached_target_temp_start_time and temps[k]['actual'] < (
					temps[k]['target'] - bed_fluctuation)):
					self._printer_not_printing_reached_target_temp_start_time = None

				if self._previous_bed_target_temp != temps[k]['target']:
					self._bed_warming_notification_was_sent = False

					# Reset time if our new target temperature is below our current temperature
					# to avoid an instant notification when the new target temp is reached
					if self._previous_bed_target_temp > temps[k]['target']:
						self._printer_not_printing_reached_target_temp_start_time = None
						self._previous_bed_target_temp = temps[k]['target']

				if target_temp_minutes_hold and self._printer_not_printing_reached_target_temp_start_time:
					if bed_warm_notify_once and self._bed_warming_notification_was_sent:
						return
					warmed_time_seconds = time.time() - self._printer_not_printing_reached_target_temp_start_time
					warmed_time_minutes = warmed_time_seconds / 60
					if warmed_time_minutes > target_temp_minutes_hold:
						self._logger.debug("Bed reached target temp for {0} minutes".format(warmed_time_minutes))
						self._printer_not_printing_reached_target_temp_start_time = None
						self._bed_warming_notification_was_sent = True
						self._previous_bed_target_temp = temps[k]['target']

						self.__send__bed_notification(settings, "bed-warmed", temps[k]['target'],
													int(warmed_time_minutes))

	# Private functions - Bed Notifications

	def __send__bed_notification(self, settings, event_code, temperature, minutes):
		# Fire IFTTT webhook
		self._ifttt_alerts.fire_event(settings, event_code, temperature)
		# Send push notification via OctoPod app
		self.__send__octopod_notification(settings, event_code, temperature, minutes)

	def __send__octopod_notification(self, settings, event_code, temperature, minutes):
		def _send_legacy_notification(server_url, apns_token, printer_id):
			url = server_url + '/v1/push_printer/bed_events'
			return self._alerts.send_bed_request(url, apns_token, printer_id, event_code, temperature, minutes)

		return self._send_base_notification(settings, False, event_code, legacy_code_block=_send_legacy_notification)

import time

from .base_notification import BaseNotification


class BedNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
		self._printer_was_printing_above_bed_low = False  # Variable used for bed cooling alerts
		self._printer_not_printing_reached_target_temp_start_time = None  # Variable used for bed warming alerts

	def set_temperature_threshold(self, settings, temperature):
		if temperature >= 0 and temperature < 200:
			settings.set(["bed_low"], temperature)
			settings.save()
			return True
		else:
			return False

	def set_temperature_duration(self, settings, minutes):
		if minutes >= 0:
			settings.set(["bed_target_temp_hold"], minutes)
			settings.save()
			return True
		else:
			return False

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

				self.__send__bed_notification(settings, "bed-cool", threshold_low, None)

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

				if target_temp_minutes_hold and self._printer_not_printing_reached_target_temp_start_time:
					warmed_time_seconds = time.time() - self._printer_not_printing_reached_target_temp_start_time
					warmed_time_minutes = warmed_time_seconds / 60
					if warmed_time_minutes > target_temp_minutes_hold:
						self._logger.debug("Bed reached target temp for {0} minutes".format(warmed_time_minutes))
						self._printer_not_printing_reached_target_temp_start_time = None

						self.__send__bed_notification(settings, "bed-warn", temps[k]['target'])

	# Private functions - Bed Notifications

	def __send__bed_notification(self, settings, event_code, temperature, minutes):
		# Fire IFTTT webhook
		self._ifttt_alerts.fire_event(settings, event_code, temperature)
		# Send push notification via Printoid app
		self._send_base_notification(settings,
									 include_image=False,
									 event_code=event_code,
									 event_param=temperature)

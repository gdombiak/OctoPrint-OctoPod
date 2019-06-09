import time
import requests


class BedNotifications:

	def __init__(self, logger):
		self._logger = logger
		self._printer_was_printing_above_bed_low = False  # Variable used for bed cooling alerts
		self._printer_not_printing_reached_target_temp_start_time = None  # Variable used for bed warming alerts

	def check_temps(self, settings, printer):
		temps = printer.get_current_temperatures()
		self._logger.debug(u"CheckTemps(): %r" % (temps,))
		if not temps:
			self._logger.debug(u"No Temperature Data")
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

			# If we are not printing and we were printing before with bed temp above bed threshold and bed temp is now below bed threshold
			if self._printer_was_printing_above_bed_low and not printer.is_printing() and threshold_low and temps[k][
				'actual'] < threshold_low:
				self._logger.debug(
					"Print done and bed temp is now below threshold {0}. Actual {1}.".format(threshold_low, temps[k]['actual']))
				self._printer_was_printing_above_bed_low = False

				self.send__bed_notification(settings, "bed-cooled", threshold_low, None)

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

						self.send__bed_notification(settings, "bed-warmed", temps[k]['target'],
													int(warmed_time_minutes))

	##~~ Private functions - Bed Notifications

	def send__bed_notification(self, settings, event_code, temperature, minutes):
		url = settings.get(["server_url"])
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		url = url + '/v1/push_printer/bed_events'

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

			last_result = self.send_bed_request(url, apns_token, printerID, event_code, temperature, minutes)

		return last_result

	def send_bed_request(self, url, apns_token, printer_id, event_code, temperature, minutes):
		data = {"tokens": [apns_token], "printerID": printer_id, "eventCode": event_code, "temperature": temperature, "silent": True}

		if minutes:
			data["minutes"] = minutes

		try:
			r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Bed Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Bed Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send Bed Notification: %s" % str(e))
			return -500

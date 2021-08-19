import time

from .alerts import Alerts


class ThermalProtectionNotifications:

	def __init__(self, logger, ifttt_alerts):
		self._logger = logger
		self._ifttt_alerts = ifttt_alerts
		self._alerts = Alerts(self._logger)
		self._last_thermal_runaway_notification_time = None  # Variable used for spacing notifications
		self._last_actual_temps = {} # Variable that helps know if we are cooling down or not
		self._last_target_temps = {} # Variable that helps know if we need to reset saved info

	def check_temps(self, settings, printer):
		temps = printer.get_current_temperatures()
		# self._logger.debug(u"CheckTemps(): %r" % (temps,))
		if not temps:
			# self._logger.debug(u"No Temperature Data")
			return

		# example dictionary from octoprint
		# {
		#   'bed': {'actual': 0.9, 'target': 0.0, 'offset': 0},
		#   'tool0': {'actual': 0.0, 'target': 0.0, 'offset': 0},
		#   'tool1': {'actual': 0.0, 'target': 0.0, 'offset': 0}
		# }
		thermal_threshold = settings.get_int(['thermal_runway_threshold'])

		if thermal_threshold > 0:
			# Check for possible thermal runaway
			for k in temps.keys():
				self.__check_thermal_runway(temps, k, thermal_threshold, settings)

	def __check_thermal_runway(self, temps, part, thermal_threshold, settings):
		thermal_threshold_minutes_frequency = settings.get_int(['thermal_threshold_minutes_frequency'])
		target_temp = temps[part]['target']
		if target_temp and target_temp > 0:
			# Check if target temp has changed
			if target_temp != self.__get_last_target_temp(part):
				# Target temp changed so store it, reset old stored info and continue
				self.__save_last_target_temp(part, target_temp)
				self.__clear_last_actual_temp(part)
			# Proceed with thermal checking
			actual_temp = temps[part]['actual']
			now = time.time()
			# Check if there is a possible thermal runaway when we are heating up more than we requested (very unusual)
			if actual_temp >= (target_temp + thermal_threshold):
				# Ignore if we are cooling down (could happen when target temp went down and actual is still higher)
				if not self.__get_last_actual_temp(part) or self.__get_last_actual_temp(part) > actual_temp:
					if not self.__get_last_actual_temp(part):
						self._logger.debug("Thermal runaway - Started to track {0}. Temp should go down. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
					else:
						self._logger.debug("Thermal runaway - Tracking {0}. Temp going down. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
					# Remember last temp so we can see if we are still cooling down
					self.__save_last_temp(part, actual_temp)
					return
				elif self.__get_last_actual_temp(part) == actual_temp:
					# Not cooling down yet and temp still the same. Give it up to 14 seconds to cool
					# down or send the alert
					cooldown_threshold = settings.get_int(['thermal_cooldown_seconds_threshold'])
					if self.__get_last_actual_temp_time(part) + cooldown_threshold > now:
						self._logger.debug("Thermal runaway - Tracking {0}. Temp NOT going down. Will wait more time. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# We can still wait more time to let things cool down
						return

				# Alert about possible thermal runaway (unless we just alerted)
				self.__thermal_runaway_detected(actual_temp, now, part, settings, target_temp,
											  thermal_threshold_minutes_frequency)
			else:
				# Check if we are below target and not warming up (more realistic case). Some firmwares
				# already perform this check but some printers still have thermal runaway disabled so this
				# check can save those printers from catching fire
				below_target_threshold = settings.get_int(['thermal_below_target_threshold'])
				warmup_threshold = settings.get_int(['thermal_warmup_seconds_threshold'])
				# Check if below target temp. Use range to say that it is below target
				if actual_temp + below_target_threshold < target_temp:
					if not self.__get_last_actual_temp(part):
						self._logger.debug("Thermal runaway - Started to track {0}. Temp should go up. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# Remember last temp so we can see if we temps are going up or not
						self.__save_last_temp(part, actual_temp)
						return
					# Check if current temp is still the same as last time we checked (or up to 1C lower)
					# Allow up to 1C lower since sometimes bed may lose half a degree
					if (actual_temp == self.__get_last_actual_temp(part) or
						self.__temp_decreased_upto(actual_temp, self.__get_last_actual_temp(part), 1)) and \
							self.__get_last_target_temp_time(part) + warmup_threshold > now:
						self._logger.debug("Thermal runaway - Tracking {0}. Temp NOT going up. Will wait more time. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# We can still wait more time to let things warm up
						return
					# Check if temp did not increase since last temp check. Task runs every 5 seconds
					# so if temp did not increase in 5 seconds then send alert
					if actual_temp <= self.__get_last_actual_temp(part):
						# Alert about possible thermal runaway (unless we just alerted)
						self.__thermal_runaway_detected(actual_temp, now, part, settings, target_temp,
														thermal_threshold_minutes_frequency)
					else:
						self._logger.debug("Thermal runaway - Tracking {0}. Temp going up. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# Save target temp again so we reset timer. This will let us send alert notification
						# only if there is no temp increase starting from now
						self.__save_last_target_temp(part, target_temp)
						# Remember last temp so we can see if we temp keeps going up
						self.__save_last_temp(part, actual_temp)
				else:
					# Temp is not above target range and is not below target range. IOW, it is in an ok range
					self._logger.debug("Thermal runaway - Temp of {0} is within range. "
									  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
					self.__clear_last_actual_temp(part)
		else:
			# No target temp is defined so clean up any tracking info
			self.__clear_last_actual_temp(part)
			self.__clear_last_target_temp(part)

	def __thermal_runaway_detected(self, actual_temp, now, part, settings, target_temp,
								 thermal_threshold_minutes_frequency):
		last_time = self._last_thermal_runaway_notification_time
		should_alert = not last_time or now > last_time + (thermal_threshold_minutes_frequency * 60)
		if should_alert:
			self._logger.warning("Possible thermal runaway detected for {0}. Actual {1} and Target {2} ".
							   format(part, actual_temp, target_temp))
			self.__send__thermal_notification(settings, "thermal-runaway")
			self._last_thermal_runaway_notification_time = now
			self.__clear_last_actual_temp(part)

	def __send__thermal_notification(self, settings, event_code):
		# Fire IFTTT webhook
		self._ifttt_alerts.fire_event(settings, event_code, "")
		# Send push notification via OctoPod app
		self.__send__octopod_notification(settings, event_code)

	def __send__octopod_notification(self, settings, event_code):
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
														   event_code, None, None)

		return last_result

	def __temp_decreased_upto(self, actual_temp, last_actual_temp, decrease):
		return actual_temp <  last_actual_temp and \
			   actual_temp > last_actual_temp - decrease

	def __save_last_temp(self, part, actual_temp):
		self._last_actual_temps[part] = (actual_temp, time.time())

	def __clear_last_actual_temp(self, part):
		# Use pop and use some default value in case key does not exist
		self._last_actual_temps.pop(part, 0)

	def __get_last_actual_temp(self, part):
		tuple = self._last_actual_temps.get(part)
		return tuple[0] if tuple else None

	def __get_last_actual_temp_time(self, part):
		tuple = self._last_actual_temps.get(part)
		return tuple[1] if tuple else None

	def __save_last_target_temp(self, part, target_temp):
		self._last_target_temps[part] = (target_temp, time.time())

	def __clear_last_target_temp(self, part):
		# Use pop and use some default value in case key does not exist
		self._last_target_temps.pop(part, 0)

	def __get_last_target_temp(self, part):
		tuple = self._last_target_temps.get(part)
		return tuple[0] if tuple else None

	def __get_last_target_temp_time(self, part):
		tuple = self._last_target_temps.get(part)
		return tuple[1] if tuple else None


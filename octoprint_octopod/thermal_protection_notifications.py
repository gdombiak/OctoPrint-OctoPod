import time

from .base_notification import BaseNotification


class ThermalProtectionNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts
		self._last_thermal_runaway_notification_time = None  # Variable used for spacing notifications
		self._last_actual_temps = {} # Variable that helps know if we are cooling down or not
		self._last_target_temps = {} # Variable that helps know if we need to reset saved info
		self._heater_timeout = False

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

	def process_received_gcode(self, line):
		# Firmware will print to terminal when printer has paused for user. If user does not respond
		# quickly then heater will timeout and will start to cool down while keeping hotend target temp
		# unmodified. We need to detect this case to not send incorrect thermal runaway alerts.
		# '//action:' messages are i18n'ed so cannot be used to detect heater timeout
		if line.startswith("echo:Press button to heat nozzle"):
			self._logger.debug("Thermal runaway - Printer paused for user and heater timed out")
			self._heater_timeout = True

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
			cooldown_threshold = settings.get_int(['thermal_cooldown_seconds_threshold'])
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
					if self.__get_last_actual_temp_time(part) + cooldown_threshold > now:
						self._logger.debug("Thermal runaway - Tracking {0}. Temp NOT going down. Will wait more time. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# We can still wait more time to let things cool down
						return
				elif self.__temp_increased_upto(actual_temp, self.__get_last_actual_temp(part), 9) and \
							self.__get_last_actual_temp_time(part) + cooldown_threshold > now:
					self._logger.debug("Thermal runaway - Tracking {0}. Temp went UP instead of DOWN. Will wait "
									   "more time. Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
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
				warmup_threshold = self.__get_warmup_threshold(settings, part)
				# Check if below target temp. Use range to say that it is below target
				if actual_temp + below_target_threshold < target_temp:
					if not self.__get_last_actual_temp(part):
						self._logger.debug("Thermal runaway - Started to track {0}. Temp should go up. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# Remember last temp so we can see if we temps are going up or not
						self.__save_last_temp(part, actual_temp)
						return
					# Check if temp is going down since heater timed out when printer paused waiting for user
					if self._heater_timeout and actual_temp <= self.__get_last_actual_temp(part) + 1:
						# Heater timed out when printer paused waiting for user and temp is still going down
						# Added 1C in case temp goes down to room temp and has minor fluctuations
						self._logger.debug("Thermal runaway - Ignore checking since heater timed out waiting for user. "
										  "Actual {1} and Target {2} ".format(part, actual_temp, target_temp))
						# Remember last temp so we can see if we temps are going up or not
						self.__save_last_temp(part, actual_temp)
						return
					# Check if current temp is still the same as last time we checked (or up to 2C lower)
					# Allow up to 1C lower since sometimes bed may lose half a degree
					if (actual_temp == self.__get_last_actual_temp(part) or
						self.__temp_decreased_upto(actual_temp, self.__get_last_actual_temp(part), 2)) and \
							self.__get_last_actual_temp_time(part) + warmup_threshold > now:
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
						# Clear up flag that tracks if heater timed out. Marlin does not print a
						# unique code to know when user pressed button to heat nozzle after
						# printer paused for user and heater timed out. So if we see temp go up
						# then we can assume user pressed button. Not ideal solution in case there
						# is a thermal runaway exactly at this time. But best we can do atm
						self._heater_timeout = False
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
		self._send_base_notification(settings, False, event_code)

	def __temp_decreased_upto(self, actual_temp, last_actual_temp, decrease):
		return last_actual_temp > actual_temp > last_actual_temp - decrease

	def __temp_increased_upto(self, actual_temp, last_actual_temp, increase):
		return last_actual_temp < actual_temp < last_actual_temp + increase

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

	def __get_warmup_threshold(self, settings, part):
		if part == 'bed':
			return settings.get_int(['thermal_warmup_bed_seconds_threshold'])
		elif part.startswith('tool'):
			return settings.get_int(['thermal_warmup_hotend_seconds_threshold'])
		else:
			return settings.get_int(['thermal_warmup_chamber_seconds_threshold'])

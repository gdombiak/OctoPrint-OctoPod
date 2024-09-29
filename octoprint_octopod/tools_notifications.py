from .base_notification import BaseNotification


class ToolsNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts, plugin_manager):
		BaseNotification.__init__(self, logger, plugin_manager)
		self._ifttt_alerts = ifttt_alerts
		self._printer_was_printing_above_tool0_low = False  # Variable used for tool0 cooling alerts
		self._printer_alerted_reached_tool0_target = False  # Variable used for tool0 warm alerts

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
			if k == 'tool0':
				tool0_threshold_low = settings.get_int(['tool0_low'])
				target_temp = settings.get(['tool0_target_temp'])
			else:
				continue

			# Check if tool0 has cooled down to specified temperature once print is finished
			# Remember if we are printing and current tool0 temp is above the low tool0 threshold
			if not self._printer_was_printing_above_tool0_low and printer.is_printing() and tool0_threshold_low and \
				temps[k]['actual'] > tool0_threshold_low:
				self._printer_was_printing_above_tool0_low = True

			# If we are not printing and we were printing before with tool0 temp above threshold and tool0 temp is now
			# below threshold
			if self._printer_was_printing_above_tool0_low and not printer.is_printing() and tool0_threshold_low \
				and temps[k]['actual'] < tool0_threshold_low:
				self._logger.debug(
					"Print done and tool0 temp is now below threshold {0}. Actual {1}.".format(tool0_threshold_low,
																							 temps[k]['actual']))
				self._printer_was_printing_above_tool0_low = False

				self.__send__tool_notification(settings, "tool0-cooled", tool0_threshold_low)

			# Check if tool0 has reached target temp and user wants to receive alerts for this event
			if temps[k]['target'] > 0 and target_temp:
				diff = temps[k]['actual'] - temps[k]['target']
				# If we have not alerted user and printer reached target temp then alert user. Only alert
				# when actual is equal to target or passed target by 5. Useful if hotend is too hot after
				# print and you want to be alerted when it cooled down to a target temp
				if not self._printer_alerted_reached_tool0_target and 0 <= diff < 5:
					self._printer_alerted_reached_tool0_target = True
					self.__send__tool_notification(settings, "tool0-warmed", temps[k]['target'])
			elif temps[k]['target'] == 0:
				# There is no target temp so reset alert flag so we can alert again
				# once a target temp is set
				self._printer_alerted_reached_tool0_target = False

	##~~ Private functions - Tool Notifications

	def __send__tool_notification(self, settings, event_code, temperature_threshold):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, event_code, temperature_threshold)
		event_param = {'Tool0Threshold': temperature_threshold}
		return self._send_base_notification(settings, False, event_code, event_param=event_param)

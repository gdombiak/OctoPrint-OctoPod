from .base_notification import BaseNotification


class SpoolManagerNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts, plugin_manager):
		BaseNotification.__init__(self, logger, plugin_manager)
		self._ifttt_alerts = ifttt_alerts

	def check_plugin_message(self, settings, printer, plugin, data):
		if (plugin == "SpoolManager" and 'type' in data and data["type"] == "warning" and 'title' in data and
			"Filament not enough" in data["title"]):
			# Send notification if printing and plugin alerted that there is not enough filament
			if self._is_printer_printing(printer):
				self._logger.info("*** SpoolManager warned not enough filament while printing ***")
				message = "{} {}".format(data["title"], data["message"])
				self.__send_spool_manager_notification(settings, message)

	# Private functions - Notifications

	def __send_spool_manager_notification(self, settings, message):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "spool_manager-not-enough-filament", "")
		return self._send_arbitrary_notification(settings, message, None)

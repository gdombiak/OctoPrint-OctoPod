import threading

from .base_notification import BaseNotification


class GcodeNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._gcode_commands = []
		self._ifttt_alerts = ifttt_alerts
		self.reset_gcode_commands()

	def get_gcode_commands(self):
		""" Returns list of GCODE commands for which notifications will be sent """
		return self._gcode_commands

	def reset_gcode_commands(self):
		""" Reset list of GCODE commands for which notifications will be sent """
		self._gcode_commands = []

	def add_gcode_commands(self, gcodeCommand):
		""" Add a new GCODE command to the list for which notifications will be sent """
		self._gcode_commands.append(gcodeCommand)

	def remove_gcode_commands(self, gcodeCommand):
		""" Remove GCODE command from list for which notifications will be sent """
		self._gcode_commands.remove(gcodeCommand)

	def process_gcode(self, settings, gcode_command):
		should_notify = False

		if gcode_command in self._gcode_commands:
			should_notify = True

		if should_notify:
			th = threading.Thread(target=self.__send__gcode_notification,
								  args=(settings, gcode_command))
			th.start()


	def __send__gcode_notification(self, settings, gcode_command):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "gcode-command", gcode_command)

		return self._send_base_notification(settings,
											include_image=False,
											event_code="gcode-command",
											event_param=gcode_command)

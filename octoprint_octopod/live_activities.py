import time

from .base_notification import BaseNotification

class LiveActivities(BaseNotification):

	__HIGH_PRIORITY = 10 # Constant value matches DeliveryPriority enum of Pushy's library
	__LOW_PRIORITY = 5 # Constant value matches DeliveryPriority enum of Pushy's library
	__MINUTES_BETWEEN_HIGH_PRIORITY = 7 # Use high priority every 7 minutes for progress notifications
	__MINUTES_BETWEEN_LOW_PRIORITY = 1 # Send up to 1 low priority notification every minute

	def __init__(self, logger, plugin_manager):
		BaseNotification.__init__(self, logger, plugin_manager)
		# TODO Test thread-safety of dictionaries
		self._live_activities = {} # Track tokens to use for updating Live Activities
		self._last_high_priority_notification = None  # Keep track of last time a high priority notification was sent
		self._last_low_priority_notification = None  # Keep track of last time a low priority notification was sent
		self._printing = False

	def register_live_activity(self, activity_id, token):
		"""
		Each Live Activity has its own APNS token used for updating the Live Activity.
		They can change during the life of the live activity. If token is None then
		unregister the live activity.

		:param activity_id: id of the live activity as provided by the iOS app
		:param token: APNS token to use for updating the live activity
		"""
		if token is None:
			self._live_activities.pop(activity_id, None)
		else:
			self._live_activities[activity_id] = token

	def on_printer_state_changed(self, settings, printer, event_payload):
		"""
		Printer status has changed. We might need to update active live activities
		if printer has a print job (printing or paused)

		:param settings: Plugin settings
		:param printer: printer object that holds printer information
		:param event_payload: payload included in the OctoPrint event
		"""
		current_printer_state_id = event_payload["state_id"]
		# Ignore other states that are not any of the following
		if current_printer_state_id != "OPERATIONAL" and current_printer_state_id != "PRINTING" and \
				current_printer_state_id != "PAUSED" and current_printer_state_id != "CLOSED" and \
				current_printer_state_id != "ERROR" and current_printer_state_id != "CLOSED_WITH_ERROR" and \
				current_printer_state_id != "OFFLINE":
			return

		was_printing = self._printing
		self._printing = current_printer_state_id == "PRINTING" or current_printer_state_id == "PAUSED"

		# Do nothing if not printing and was not printing
		if not self._printing and not was_printing:
			return

		# Do nothing if no live activities are registered
		if not self._live_activities:
			return

		(url, printer_status, completion, print_time_left_in_seconds) = self.__get_notification_data(settings, printer)

		# Send live activity notification. Use high priority notification for changes of status
		tokens = list(self._live_activities.values())
		self._alerts.send_live_activity_notification(url, tokens, printer_status, completion,
													 print_time_left_in_seconds, self._printing,
													 self.__HIGH_PRIORITY)

		self._logger.debug("Live activity - Activities: {0}, Printing: {1}, Progress: {2}, State: {3} and Time Left: {4}".
						   format(len(tokens), self._printing, completion, printer_status, print_time_left_in_seconds))

		if self._printing:
			# Record last time a high priority notification was sent
			self._last_high_priority_notification = time.time()
		else:
			# Live Activities were ended since we are no longer printing so clean up list
			self._live_activities.clear()

	def on_print_progress(self, settings, printer):
		# Do nothing if no live activities are registered
		if not self._live_activities:
			return

		if self._printing:
			(url, printer_status, completion, print_time_left_in_seconds) = self.__get_notification_data(settings,
																										 printer)
			# Assume low priority by default for the notification
			# iOS has a limit of updates of live activities per hour (unknown how much) so we need
			# to control number of high priority notifications to send per hour.
			# Low priority notifications do not ensure that UI of live activity is updated
			priority = LiveActivities.__LOW_PRIORITY
			if self._last_high_priority_notification is not None:
				elapsed_minutes = (time.time() - self._last_high_priority_notification) / 60
				if elapsed_minutes >= LiveActivities.__MINUTES_BETWEEN_HIGH_PRIORITY:
					priority = LiveActivities.__HIGH_PRIORITY

			# Some print jobs do not take many minutes to print so use high priority
			# on some pre-defined milestones.
			# TODO Possible optimization is to only do this based on job duration
			if completion == 20 or completion == 40 or completion == 60 or completion == 80:
				priority = LiveActivities.__HIGH_PRIORITY

			# Ignore too frequent low priority notifications to minimize
			# network load on the APNS service
			if priority == LiveActivities.__LOW_PRIORITY and self._last_low_priority_notification is not None:
				elapsed_minutes = (time.time() - self._last_low_priority_notification) / 60
				if elapsed_minutes < LiveActivities.__MINUTES_BETWEEN_LOW_PRIORITY:
					self._logger.debug(
						"Live activity - Skipped low priority notification. Progress: {0}".
						format(completion))
					return

			# Send live activity notification with proper priority to manage iOS budget of updates
			tokens = list(self._live_activities.values())
			self._alerts.send_live_activity_notification(url, tokens, printer_status, completion,
														 print_time_left_in_seconds, True,
														 priority)

			self._logger.debug(
				"Live activity - Activities: {0}, Priority: {1}, Progress: {2}, State: {3} and Time Left: {4}".
				format(len(tokens), priority, completion, printer_status, print_time_left_in_seconds))

			if priority == LiveActivities.__HIGH_PRIORITY:
				# Record last time a high priority notification was sent
				self._last_high_priority_notification = time.time()
			else:
				self._last_low_priority_notification = time.time()

	def __get_service_url(self, settings):
		server_url = self._get_server_url(settings)
		if not server_url or not server_url.strip():
			# No APNS server has been defined so do nothing
			return
		return server_url + '/v1/push_printer/live_activity'

	def __get_notification_data(self, settings, printer):
		url = self.__get_service_url(settings)
		current_data = printer.get_current_data()
		printer_status = None
		(completion, print_time_in_seconds, print_time_left_in_seconds) = self._get_progress_data(printer)
		completion = round(completion) if completion is not None else None

		if "state" in current_data and current_data["state"] is not None:
			printer_status = current_data["state"]["text"]

		# All fields need to be present for iOS to decode notification and update live activity
		# Assume default values when printer is operational (usually when user cancelled print)
		if printer.get_state_id() == "OPERATIONAL":
			if completion is None:
				completion = 0
			if print_time_left_in_seconds is None:
				print_time_left_in_seconds = 0

		return url, printer_status, completion, print_time_left_in_seconds

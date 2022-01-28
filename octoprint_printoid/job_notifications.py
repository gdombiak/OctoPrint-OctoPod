import threading

from .base_notification import BaseNotification


class JobNotifications(BaseNotification):
	_lastPrinterState = None

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts

	def set_progress_mode(self, settings, mode):
		if mode == '0' or mode == '10' or mode == '25' or mode == '50' or mode == '100':
			settings.set(["progress_type"], mode)
			settings.save()
			return True
		else:
			return False

	def on_print_progress(self, settings, progress):
		progress_type = settings.get(["progress_type"])
		if progress_type == '0':
			# Print notification disabled
			return

		elif progress_type == '10':
			# Print notifications every 10%
			# 100% is sent via #send__printer_state_changed
			if progress > 0 and progress < 100 and progress % 10 == 0:
				self.send__print_job_progress_value(settings, progress)
			return

		elif progress_type == '25':
			# Print notifications every 25%
			# 100% is sent via #send__printer_state_changed
			if progress > 0 and progress < 100 and progress % 25 == 0:
				self.send__print_job_progress_value(settings, progress)
			return

		elif progress_type == '50':
			# Print notifications at 50% and 100%
			# 100% is sent via #send__printer_state_changed
			if progress == 50:
				self.send__print_job_progress_value(settings, progress)
			return

		else:
			# Assume print notification only at 100% (once done printing)
			# 100% is sent via #send__printer_state_changed
			return

	def send__print_job_progress_value(self, settings, progress):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "print-progress", progress)
		return self._send_base_notification(settings,
											include_image=True,
											event_code="print-progress",
											event_param=progress)

	def send__printer_state_changed(self, settings, printer, event_payload, server_url=None,
									camera_snapshot_url=None,
									webcam_flipH=None, webcam_flipV=None, webcam_rotate90=None):
		progress_type = settings.get(["progress_type"])
		if progress_type == '0':
			# Print notification disabled
			return
		if server_url:
			url = server_url
		else:
			url = settings.get(["server_url"])
		if not url or not url.strip():
			# No FCM server has been defined so do nothing
			return -1

		# Gather information about progress completion of the job
		completion = None
		was_printing = False
		current_data = printer.get_current_data()

		if "progress" in current_data and current_data["progress"] is not None \
			and "completion" in current_data["progress"] and current_data["progress"][
			"completion"] is not None:
			completion = current_data["progress"]["completion"]

		current_printer_state_id = event_payload["state_id"]

		# Ignore other states that are not any of the following
		if current_printer_state_id != "OPERATIONAL" and current_printer_state_id != "PRINTING" and \
			current_printer_state_id != "PAUSED" and current_printer_state_id != "CLOSED" and \
			current_printer_state_id != "ERROR" and current_printer_state_id != "CLOSED_WITH_ERROR" and \
			current_printer_state_id != "OFFLINE" and current_printer_state_id != "FINISHING":
			return -3

		current_printer_state = event_payload["state_string"]
		if current_printer_state == self._lastPrinterState:
			# OctoPrint may report the same state more than once so ignore dups
			return -4

		if self._lastPrinterState is not None and self._lastPrinterState.startswith('Printing'):
			was_printing = True
		self._lastPrinterState = current_printer_state

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			return -2

		# See if user asked to delay this notification
		print_complete_delay_seconds = settings.get_int(['print_complete_delay_seconds'])

		if print_complete_delay_seconds == 0 or completion < 100 or not (
				was_printing and current_printer_state_id == "FINISHING"):
			last_result = self.__send_print_complete_or_silent_notification(camera_snapshot_url,
																			completion,
																			current_data,
																			current_printer_state,
																			current_printer_state_id,
																			settings,
																			tokens, url,
																			was_printing,
																			webcam_flipH,
																			webcam_flipV,
																			webcam_rotate90)
		else:
			delayed_task = threading.Timer(print_complete_delay_seconds,
										   self.__send_print_complete_or_silent_notification,
										   [camera_snapshot_url, completion, current_data,
											current_printer_state,
											current_printer_state_id, settings, tokens, url,
											was_printing,
											webcam_flipH, webcam_flipV, webcam_rotate90])
			delayed_task.start()
			# this value is ignored since it is used for testing
			last_result = 0

		return last_result

	# Private functions - Print Job Notifications

	def __send_print_complete_or_silent_notification(self, camera_snapshot_url, completion,
													 current_data,
													 current_printer_state,
													 current_printer_state_id, settings,
													 tokens, url, was_printing, webcam_flipH,
													 webcam_flipV,
													 webcam_rotate90):
		# Get a snapshot of the camera
		image = None
		if was_printing and current_printer_state_id == "FINISHING":
			# Only include image when print is complete. This is an optimization to avoid sending
			# images that won't be rendered by the app

			try:
				# Reduce resolution of image to prevent 400 error when uploading content
				# Besides this saves network bandwidth and Android device or WearOS
				# cannot tell the difference in resolution
				image_obj = Image.open(BytesIO(image))
				x, y = image_obj.size
				if x > 1640 or y > 1232:
					size = 1640, 1232
					image_obj.thumbnail(size, Image.ANTIALIAS)
					output = BytesIO()
					image_obj.save(output, format="JPEG")
					image = output.getvalue()
					output.close()
			except Exception as e:
				self._logger.debug("Error reducing resolution of image: %s" % str(e))

			if webcam_flipH is not None:
				hflip = webcam_flipH
			else:
				hflip = settings.get(["webcam_flipH"])
			if webcam_flipV is not None:
				vflip = webcam_flipV
			else:
				vflip = settings.get(["webcam_flipV"])
			if webcam_rotate90 is not None:
				rotate = webcam_rotate90
			else:
				rotate = settings.get(["webcam_rotate90"])
			try:
				if camera_snapshot_url:
					camera_url = camera_snapshot_url
				else:
					camera_url = settings.get(["camera_snapshot_url"])
				if camera_url and camera_url.strip():
					image = self.image(camera_url, hflip, vflip, rotate)
			except:
				self._logger.info("Could not load image from url")

		# Send IFTTT Notifications
		if current_printer_state_id == "ERROR":
			self._ifttt_alerts.fire_event(settings, "printer-error", current_printer_state)
		elif current_printer_state_id == "FINISHING" and was_printing:
			self._ifttt_alerts.fire_event(settings, "print-complete", "")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# Android app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			fcm_token = token["fcmToken"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the Android app. Usually one for local address and one for public address
			if fcm_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(fcm_token)

			printer_name = token["printerName"]

			if current_printer_state_id == "ERROR":
				self._logger.debug(
					"Sending notification for error message: %s (%s)" % (current_printer_state, printer_name))
				last_result = self.send__print_status_notification(settings, False, "printer-error", current_printer_state)

			elif current_printer_state_id == "FINISHING" and was_printing:
				last_result = self.send__print_status_notification(settings, True, "print-complete")

			else:
				last_result = self.send__print_status_notification(settings, False, "printer-state", current_printer_state)

		return last_result

	def send__print_status_notification(self, settings, include_image, event_code, event_param=None):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, event_code, event_param)
		return self._send_base_notification(settings,
											include_image,
											event_code,
											event_param)

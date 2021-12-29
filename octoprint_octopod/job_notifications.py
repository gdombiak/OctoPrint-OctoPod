import threading

from .base_notification import BaseNotification


class JobNotifications(BaseNotification):
	_lastPrinterState = None

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._ifttt_alerts = ifttt_alerts

	def on_print_progress(self, settings, progress):
		progress_type = settings.get(["progress_type"])
		if progress_type == '0':
			# Print notification disabled
			return
		elif progress_type == '25':
			# Print notifications at 25%, 50%, 75% and 100%
			# 100% is sent via #send__print_job_notification
			if progress == 25 or progress == 50 or progress == 75:
				self.send__print_job_progress(settings, progress)
			return
		elif progress_type == '50':
			# Print notifications at 50% and 100%
			# 100% is sent via #send__print_job_notification
			if progress == 50:
				self.send__print_job_progress(settings, progress)
			return
		else:
			# Assume print notification only at 100% (once done printing)
			# 100% is sent via #send__print_job_notification
			return

	def send__print_job_progress(self, settings, progress):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "print-progress", progress)

		def _send_silent_notification(apns_token, image, printer_id, url):
			self._alerts.send_job_request(apns_token, None, printer_id, "Printing", progress, url)

		return self._send_base_notification(settings, True, "Print progress", event_param=progress,
											silent_code_block=_send_silent_notification)

	def send__print_job_notification(self, settings, printer, event_payload, server_url=None, camera_snapshot_url=None,
									 webcam_flipH=None, webcam_flipV=None, webcam_rotate90=None, test=False):
		progress_type = settings.get(["progress_type"])
		if progress_type == '0' and not test:
			# Print notification disabled
			return
		if server_url:
			url = server_url
		else:
			url = self._get_server_url(settings)
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		url = url + '/v1/push_printer'

		# Gather information about progress completion of the job
		completion = None
		was_printing = False
		current_data = printer.get_current_data()
		if "progress" in current_data and current_data["progress"] is not None \
				and "completion" in current_data["progress"] and current_data["progress"][
			"completion"] is not None:
			completion = current_data["progress"]["completion"]

		current_printer_state_id = event_payload["state_id"]
		if not test:
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
		else:
			current_printer_state_id = "OPERATIONAL"
			current_printer_state = "Operational"
			completion = 100

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		# See if user asked to delay this notification
		print_complete_delay_seconds = settings.get_int(['print_complete_delay_seconds'])

		if test or print_complete_delay_seconds == 0 or completion < 100 or not (
				was_printing and current_printer_state_id == "FINISHING"):
			last_result = self.__send_print_complete_or_silent_notification(camera_snapshot_url, completion,
																			current_data, current_printer_state,
																			current_printer_state_id, settings, test,
																			tokens, url, was_printing, webcam_flipH,
																			webcam_flipV, webcam_rotate90)
		else:
			delayed_task = threading.Timer(print_complete_delay_seconds,
										   self.__send_print_complete_or_silent_notification,
										   [camera_snapshot_url, completion, current_data, current_printer_state,
											current_printer_state_id, settings, test, tokens, url, was_printing,
											webcam_flipH, webcam_flipV, webcam_rotate90])
			delayed_task.start()
			# this value is ignored since it is used for testing
			last_result = 0

		return last_result

	# Private functions - Print Job Notifications

	def __send_print_complete_or_silent_notification(self, camera_snapshot_url, completion, current_data,
													 current_printer_state, current_printer_state_id, settings, test,
													 tokens, url, was_printing, webcam_flipH, webcam_flipV,
													 webcam_rotate90):
		# Get a snapshot of the camera
		image = None
		if (was_printing and current_printer_state_id == "FINISHING") or test:
			# Only include image when print is complete. This is an optimization to avoid sending
			# images that won't be rendered by the app
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
		elif (current_printer_state_id == "FINISHING" and was_printing) or test:
			self._ifttt_alerts.fire_event(settings, "print-complete", "")
		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			apns_token = token["apnsToken"]
			printer_id = token["printerID"]

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
				if current_printer_state_id == "ERROR":
					self._logger.debug(
						"Sending notification for error message: %s (%s)" % (current_printer_state, printer_name))
					last_result = self._alerts.send_alert(settings, apns_token, url, printer_name,
														  current_printer_state, None, None)
				elif (current_printer_state_id == "FINISHING" and was_printing) or test:
					apns_category = None
					apns_dict = None
					if ("job" in current_data and "file" in current_data["job"] and "path" in current_data["job"][
						"file"] and current_data["job"]["file"]["path"] is not None and "origin" in current_data["job"][
						"file"] and current_data["job"]["file"]["origin"] is not None):
						# Define APNS Category so notification shows "Print Again" button
						apns_category = "printComplete"
						# Include file information to print again
						apns_dict = {'filePath': current_data['job']['file']['path'],
									 'fileOrigin': current_data['job']['file']['origin']}
					last_result = self._alerts.send_alert_code(settings, language_code, apns_token, url, printer_name,
															   "Print complete", apns_category, image, None, apns_dict)
					# Skip the silent notification for finishing at 100%. One for operational at 100% will be sent later
					continue

				# Send silent notification so that OctoPod app can update complications of Apple Watch app
				self._alerts.send_job_request(apns_token, image, printer_id, current_printer_state, completion, url,
											  test)

			else:
				if current_printer_state_id == "FINISHING":
					# Legacy mode was not sending a notification for this state
					continue

				if image is None and completion == 100 and current_printer_state_id == "OPERATIONAL":
					# Legacy used to include an image only under this state
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

				# Legacy mode that uses silent notifications. As user update OctoPod app then they will automatically
				# switch to the new mode
				last_result = self._alerts.send_job_request(apns_token, image, printer_id, current_printer_state,
															completion, url, test)
		return last_result


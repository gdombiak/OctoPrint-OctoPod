from io import BytesIO ## for Python 2 & 3

import requests
from PIL import Image

from .alerts import Alerts


class JobNotifications:
	_lastPrinterState = None

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)

	def send__print_job_notification(self, settings, printer, event_payload, server_url=None, camera_snapshot_url=None,
									 test=False):
		if server_url:
			url = server_url
		else:
			url = settings.get(["server_url"])
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

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

		# Get a snapshot of the camera
		image = None
		if (was_printing and current_printer_state_id == "FINISHING") or test:
			# Only include image when print is complete. This is an optimization to avoid sending
			# images that won't be rendered by the app
			try:
				if camera_snapshot_url:
					camera_url = camera_snapshot_url
				else:
					camera_url = settings.get(["camera_snapshot_url"])
				if camera_url and camera_url.strip():
					image = self.image(settings)
			except:
				self._logger.info("Could not load image from url")

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
					last_result = self._alerts.send_alert(apns_token, url, printer_name, current_printer_state, None,
														  None)
				elif (current_printer_state_id == "FINISHING" and was_printing) or test:
					last_result = self._alerts.send_alert_code(language_code, apns_token, url, printer_name,
															   "Print complete", None, image)
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
					try:
						if camera_snapshot_url:
							camera_url = camera_snapshot_url
						else:
							camera_url = settings.get(["camera_snapshot_url"])
						if camera_url and camera_url.strip():
							image = self.image(settings)
					except:
						self._logger.info("Could not load image from url")

				# Legacy mode that uses silent notifications. As user update OctoPod app then they will automatically
				# switch to the new mode
				last_result = self._alerts.send_job_request(apns_token, image, printer_id, current_printer_state,
															completion, url, test)

		return last_result

	# Private functions - Print Job Notifications

	def image(self, settings):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		snapshot_url = settings.get(["camera_snapshot_url"])
		if not snapshot_url:
			return None

		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True).content

		hflip = settings.global_get(["webcam", "flipH"])
		vflip = settings.global_get(["webcam", "flipV"])
		rotate = settings.global_get(["webcam", "rotate90"])

		if hflip or vflip or rotate:
			try:
				# https://www.blog.pythonlibrary.org/2017/10/05/how-to-rotate-mirror-photos-with-python/
				image_obj = Image.open(BytesIO(image))
				if hflip:
					image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
				if vflip:
					image_obj = image_obj.transpose(Image.FLIP_TOP_BOTTOM)
				if rotate:
					image_obj = image_obj.rotate(90)

				# https://stackoverflow.com/questions/646286/python-pil-how-to-write-png-image-to-string/5504072
				output = BytesIO()
				image_obj.save(output, format="JPEG")
				image = output.getvalue()
				output.close()
			except Exception as e:
				self._logger.debug( "Error rotating image: %s" % str(e) )

		return image

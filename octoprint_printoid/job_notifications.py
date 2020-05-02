from io import BytesIO ## for Python 2 & 3

import requests
from PIL import Image

from .alerts import Alerts


class JobNotifications:
	_lastPrinterState = None

	def __init__(self, logger):
		self._logger = logger
		self._alerts = Alerts(self._logger)


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
		url = settings.get(["server_url"])
		if not url or not url.strip():
			# No FCM server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			return -2

		# Get a snapshot of the camera
		image = None
		try:
			camera_url = settings.get(["camera_snapshot_url"])
			if camera_url and camera_url.strip():
				image = self.image(camera_url, settings)
		except:
			self._logger.info("Could not load image from url")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# Android app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			fcm_token = token["fcmToken"]
			printer_id = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the Android app. Usually one for local address and one for public address
			if fcm_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(fcm_token)

			if 'printerName' in token and token["printerName"] is not None:
				# We can send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				last_result = self._alerts.send_alert_code(fcm_token, url, printer_id, printer_name,
														   "print-progress", image=image, event_param=progress)
		return last_result


	def send__printer_state_changed(self, settings, printer, event_payload, server_url=None, camera_snapshot_url=None):
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

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No Android devices were registered so skip notification
			return -2

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

		# Get a snapshot of the camera
		image = None
		if was_printing:
			try:
				if camera_snapshot_url:
					camera_url = camera_snapshot_url
				else:
					camera_url = settings.get(["camera_snapshot_url"])
				if camera_url and camera_url.strip():
					image = self.image(camera_url, settings)
			except:
				self._logger.info("Could not load image from url")

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# Android app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			fcm_token = token["fcmToken"]
			printer_id = token["printerID"]
			printer_name = token["printerName"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the Android app. Usually one for local address and one for public address
			if fcm_token in used_tokens:
				continue
				
			# Keep track of tokens that received a notification
			used_tokens.append(fcm_token)

			if 'printerName' in token and token["printerName"] is not None:
				if current_printer_state_id == "ERROR":
					self._logger.debug(
						"Sending notification for error message: %s (%s)" % (current_printer_state, printer_name))
					last_result = self._alerts.send_alert_code(fcm_token, url, printer_id, printer_name,
															   "printer-error", image=None, event_param=current_printer_state)
					
				elif (current_printer_state_id == "FINISHING" and was_printing):
					last_result = self._alerts.send_alert_code(fcm_token, url, printer_id, printer_name,
															   "print-complete", image)
															   
				else:
					last_result = self._alerts.send_alert_code(fcm_token, url, printer_id, printer_name,
															   "printer-state", image=None, event_param=current_printer_state)

		return last_result

	# Private functions - Print Job Notifications

	def image(self, snapshot_url, settings):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""

		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True).content

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
			self._logger.debug( "Error reducing resolution of image: %s" % str(e) ) 

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

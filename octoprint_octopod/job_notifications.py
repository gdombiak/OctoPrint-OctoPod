import StringIO
import json

import requests
from PIL import Image


class JobNotifications:

	_lastPrinterState = None

	def __init__(self, logger):
		self._logger = logger

	def send__print_job_notification(self, settings, printer, server_url = None, camera_snapshot_url = None, test = False):
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
		current_data = printer.get_current_data()
		if "progress" in current_data and current_data["progress"] is not None \
				and "completion" in current_data["progress"] and current_data["progress"][
			"completion"] is not None:
			completion = current_data["progress"]["completion"]

		current_printer_state_id = printer.get_state_id()
		if not test:
			# Ignore other states that are not any of the following
			if current_printer_state_id != "OPERATIONAL" and current_printer_state_id != "PRINTING" and \
				current_printer_state_id != "PAUSED" and current_printer_state_id != "CLOSED" and \
				current_printer_state_id != "ERROR" and current_printer_state_id != "CLOSED_WITH_ERROR" and \
				current_printer_state_id != "OFFLINE":
				return -3

			current_printer_state = printer.get_state_string()
			if current_printer_state == self._lastPrinterState:
				# OctoPrint may report the same state more than once so ignore dups
				return -4

			self._lastPrinterState = current_printer_state
		else:
			current_printer_state_id = "OPERATIONAL"
			current_printer_state = "Operational"
			completion = 100

		# Get a snapshot of the camera
		image = None
		if completion == 100 and current_printer_state_id == "OPERATIONAL":
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

			last_result = self.send_job_request(apns_token, image, printer_id, current_printer_state, completion, url, test)

		return last_result

	# Private functions - Print Job Notifications

	def send_job_request(self, apns_token, image, printer_id, printer_state, completion, url, test = False):
		data = {"tokens": [apns_token], "printerID": printer_id, "printerState": printer_state, "silent": True}

		if completion:
			data["printerCompletion"] = completion

		if test:
			data["test"] = True

		try:
			if image:
				files = {}
				files['image'] = ("image.jpg", image, "image/jpeg")
				files['json'] = (None, json.dumps(data), "application/json")

				r = requests.post(url, files=files)
			else:
				r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Print Job Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Print Job Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send message: %s" % str(e))
			return -500

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
			# https://www.blog.pythonlibrary.org/2017/10/05/how-to-rotate-mirror-photos-with-python/
			image_obj = Image.open(StringIO.StringIO(image))
			if hflip:
				image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
			if vflip:
				image_obj = image_obj.transpose(Image.FLIP_TOP_BOTTOM)
			if rotate:
				image_obj = image_obj.rotate(90)

			# https://stackoverflow.com/questions/646286/python-pil-how-to-write-png-image-to-string/5504072
			output = StringIO.StringIO()
			image_obj.save(output, format="JPEG")
			image = output.getvalue()
			output.close()
		return image

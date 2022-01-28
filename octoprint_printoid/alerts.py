# coding=utf-8
import json

import requests


class Alerts:

	# Flag to indicate if we should use FCM for development or production
	_use_dev = False

	def __init__(self, logger):
		self._logger = logger

	def send_alert_code(self, fcm_token, url, printer_id, printer_name, event_code, image=None, event_param=None):
		self._logger.info("//// Send alert to Printoid: '%s' with value %s (%s)" % (event_code, event_param, printer_name))

		data = {
			"name": printer_name,
			"data": {
				"type": "alert",
				"printer_name": printer_name,
				"printer_id": printer_id,
				"event_code": event_code,
				"event_param": event_param
			},
			"tokens": [fcm_token]
		}

		headers = {
			"Content-type": "application/json"
		}

		try:
			#if image:
			#	files = {"image": ("image.jpg", image, "image/jpeg"),
			#			 "json": (None, json.dumps(data), "application/json")}
			#	r = requests.post(url, headers=headers, files=files)
			#else:
			#	r = requests.post(url, headers=headers, json=data)
			r = requests.post(url, headers=headers, json=data)

			if r.status_code >= 400:
				self._logger.info("Notification Response: %s" % str(r.content))

			else:
				self._logger.debug("Notification Response code: %d" % r.status_code)

			return r.status_code

		except Exception as e:
			self._logger.warn("Could not send message: %s" % str(e))
			return -500

# coding=utf-8
import json

import requests


class Alerts:

	# Flag to indicate if we should use FCM for development or production
	_use_dev = False

	def __init__(self, logger):
		self._logger = logger

	def send_alert_code(self, language_code, fcm_token, url, printer_id, printer_name, event_code, category=None, image=None, event_param=None):
		self._logger.info("//// Send alert to Printoid: '%s' (%s)" % (event_code, printer_name))

		data = {
			"name": printer_name, 
			"data": {
				"type": "alert",
				"printer_name": printer_name,
				"printer_id": printer_id,
				"event_code": event_code,
				"event_param": event_param
			},
			"to": fcm_token, 
			"android_channel_id": "push-notifs-channel", 
			"sound": "default"
		}

		if category is not None:
			data["category"] = category

		headers = {
			"Content-type": "application/json", 
			"Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3"
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

	def send_job_request(self, fcm_token, image, printer_id, printer_name, printer_state, completion, url):
		self._logger.info("//// Send job request to Printoid")
		
		data = {
			"name": printer_name, 
			"data": {
				"type": "job",
				"printer_name": printer_name,
				"printer_id": printer_id,
				"printer_state": printer_state,
				"print_completed": completion
			},
			"to": fcm_token, 
			"android_channel_id": "push-notifs-channel", 
			"sound": "default"
		}

		headers = {
			"Content-type": "application/json", 
			"Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3"
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
				self._logger.info(
					"Silent Print Job Notification Response: %s. State: %s" % (str(r.content), printer_state))

			else:
				self._logger.debug(
					"Silent Print Job Notification Response code: %d. State: %s" % (r.status_code, printer_state))

			return r.status_code

		except Exception as e:
			self._logger.info("Could not send Silent job message: %s State: %s" % (str(e), printer_state))
			return -500



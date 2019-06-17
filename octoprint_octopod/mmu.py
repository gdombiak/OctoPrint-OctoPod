import time
import requests


class MMUAssistance:

	def __init__(self, logger):
		self._logger = logger
		self._mmu_lines_skipped = None
		self._last_notification = None  # Keep track of when was user alerted last time. Helps avoid spamming

	def process_gcode(self, settings, line):
		# MMU user assistance detection
		# Firmware will use 2 different lines to indicate the there is an MMU issue
		# and user assistance is required. There could be other lines present in the
		# terminal between the 2 relevant lines

		# if line.startswith("Not SD printing"):
		if line.startswith("mmu_get_response - begin move: T-code"):
			self._mmu_lines_skipped = 0
		else:
			if self._mmu_lines_skipped is not None:
				if self._mmu_lines_skipped > 5:
					# We give up waiting for the second line to be detected. False alert.
					# Reset counter
					self._mmu_lines_skipped = None
				# elif line.startswith("wait"):
				elif line.startswith("mmu_get_response() returning: 0"):
					# Check if we never alerted or 5 minutes have passed since last alert
					mmu_interval = settings.get_int(['mmu_interval'])
					if self._last_notification is None or (time.time() - self._last_notification) / 60 > mmu_interval:
						self._logger.info("*** MMU Requires User Assistance ***")
						# Record last time we sent notification
						self._last_notification = time.time()
						# Send APNS Notification only if interval is not zero (user requested to
						# shutdown this notification)
						if mmu_interval > 0:
							self.send__mmu_notification(settings)
					# Second line found, reset counter now
					self._mmu_lines_skipped = None
				else:
					self._mmu_lines_skipped += 1

		# Always return what we parsed
		return line

	##~~ Private functions - MMU Notifications

	def send__mmu_notification(self, settings):
		url = settings.get(["server_url"])
		if not url or not url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

		url = url + '/v1/push_printer/code_events'

		# For each registered token we will send a push notification
		# We do it individually since 'printerID' is included so that
		# iOS app can properly render local notification with
		# proper printer name
		used_tokens = []
		last_result = None
		for token in tokens:
			apns_token = token["apnsToken"]
			printerID = token["printerID"]

			# Ignore tokens that already received the notification
			# This is the case when the same OctoPrint instance is added twice
			# on the iOS app. Usually one for local address and one for public address
			if apns_token in used_tokens:
				continue
			# Keep track of tokens that received a notification
			used_tokens.append(apns_token)

			last_result = self.send_mmu_request(url, apns_token, printerID)

		return last_result

	def send_mmu_request(self, url, apns_token, printer_id):
		data = {"tokens": [apns_token], "printerID": printer_id, "eventCode": "mmu-event", "silent": True}

		try:
			r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("MMU Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("MMU Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send MMU Notification: %s" % str(e))
			return -500

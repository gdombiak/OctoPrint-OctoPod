import requests


class IFTTTAlerts:

	def __init__(self, logger):
		self._logger = logger

	def fire_event(self, settings, event, value1):
		ifttt_key = settings.get(["ifttt_key"])
		if not ifttt_key or not ifttt_key.strip():
			# No IFTTT key has been defined so do nothing
			return -1

		ifttt_name = settings.get(["ifttt_name"])
		if not ifttt_name or not ifttt_name.strip():
			# No printer name for IFTTT has been defined so do nothing
			return -1

		try:
			ifttt_event = "octopod-" + event
			url = "https://maker.ifttt.com/trigger/%s/with/key/%s" % (ifttt_event, ifttt_key)

			payload = {'value1': ifttt_name, 'value2': value1, 'value3': ""}

			response = requests.post(url, json=payload)

			if response.status_code == 200:
				self._logger.debug("IFTTT event (%s) fired!" % ifttt_event)
			else:
				self._logger.debug(
					"Error firing IFTTT event (%s). Response: %s" % (ifttt_event, str(response.status_code)))
		except Exception as e:
			self._logger.warn("Could not send IFTTT event: %s" % str(e))

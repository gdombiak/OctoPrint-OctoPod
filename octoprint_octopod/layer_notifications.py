from .alerts import Alerts


class LayerNotifications:

	def __init__(self, logger, ifttt_alerts):
		self._logger = logger
		self._ifttt_alerts = ifttt_alerts
		self._alerts = Alerts(self._logger)
		self.reset_layers()

	def get_layers(self):
		""" Returns list of layers for which notifications will be sent """
		return self._layers

	def reset_layers(self):
		""" Reset list of layers for which notifications will be sent """
		self._layers = []  # Variable used for tracking layer numbers to notify. Values are strings

	def add_layer(self, layer):
		""" Add a new layer to the list of layers for which notifications will be sent """
		self._layers.append(layer)

	def remove_layer(self, layer):
		""" Remove layer from list of layers for which notifications will be sent """
		self._layers.remove(layer)

	def layer_changed(self, settings, current_layer):
		if current_layer in self._layers:
			self.__send__layer_notification(settings, current_layer)

	def __send__layer_notification(self, settings, current_layer):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "layer-changed", current_layer)

		server_url = settings.get(["server_url"])
		if not server_url or not server_url.strip():
			# No APNS server has been defined so do nothing
			return -1

		tokens = settings.get(["tokens"])
		if len(tokens) == 0:
			# No iOS devices were registered so skip notification
			return -2

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

			if 'printerName' in token and token["printerName"] is not None:
				# We can send non-silent notifications (the new way) so notifications are rendered even if user
				# killed the app
				printer_name = token["printerName"]
				language_code = token["languageCode"]
				url = server_url + '/v1/push_printer'

				last_result = self._alerts.send_alert_code(settings, language_code, apns_token, url, printer_name,
														   "layer_changed", None, None, current_layer)

		return last_result

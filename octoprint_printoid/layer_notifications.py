from .base_notification import BaseNotification


class LayerNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts):
		BaseNotification.__init__(self, logger)
		self._layers = []
		self._ifttt_alerts = ifttt_alerts
		self.reset_layers()

	def get_layers(self):
		""" Returns list of layers for which notifications will be sent """
		return self._layers # Variable used for tracking layer numbers to notify. Values are strings

	def reset_layers(self):
		""" Reset list of layers for which notifications will be sent """
		self._layers = []

	def add_layer(self, layer):
		""" Add a new layer to the list of layers for which notifications will be sent """
		self._layers.append(layer)

	def remove_layer(self, layer):
		""" Remove layer from list of layers for which notifications will be sent """
		self._layers.remove(layer)

	def layer_changed(self, settings, current_layer):
		first_layers = settings.get_int(['notify_first_X_layers'])
		if current_layer in self._layers:
			# User specified they wanted to get a notification when print started printing at this layer
			self.__send__layer_notification(settings, current_layer)
		elif first_layers > 0 and 1 < int(current_layer) <= first_layers + 1:
			# Send a picture for first X layers (only send once layer was printed)
			self.__send__layer_notification(settings, current_layer)

	def __send__layer_notification(self, settings, current_layer):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "layer-changed", current_layer)

		return self._send_base_notification(settings,
											include_image=True,
											event_code="layer-changed",
											event_param=current_layer)

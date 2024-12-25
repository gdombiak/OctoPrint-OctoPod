from .base_notification import BaseNotification


class LayerNotifications(BaseNotification):

	def __init__(self, logger, ifttt_alerts, plugin_manager):
		BaseNotification.__init__(self, logger, plugin_manager)
		self._layers = []
		self._ifttt_alerts = ifttt_alerts
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
		permanent_layers = settings.get(['notify_layers'])
		if current_layer in self._layers:
			# User specified they wanted to get a notification when print started printing at this layer
			self.__send__layer_notification(settings, current_layer)
		elif int(current_layer) in permanent_layers:
			# Send a notification with a picture when starting to print layer configured via plugin's UI
			self.__send__layer_notification(settings, current_layer)

	def __send__layer_notification(self, settings, current_layer):
		# Send IFTTT Notifications
		self._ifttt_alerts.fire_event(settings, "layer-changed", current_layer)
		event_param = {'PrintLayer': current_layer}
		return self._send_base_notification(settings, True, "layer_changed", event_param=event_param)

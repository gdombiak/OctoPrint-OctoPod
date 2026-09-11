from copy import deepcopy
from types import SimpleNamespace

import pytest


class FakeSettings:
	"""Small in-memory substitute for the PluginSettings methods used by tests."""

	def __init__(self, values=None, global_values=None):
		self.values = deepcopy(values or {})
		self.global_values = deepcopy(global_values or {})
		self.save_count = 0

	def get(self, path):
		return self.values.get(path[0])

	def get_boolean(self, path):
		return bool(self.get(path))

	def get_int(self, path):
		value = self.get(path)
		return int(value) if value is not None else None

	def set(self, path, value):
		self.values[path[0]] = deepcopy(value)

	def global_get(self, path):
		value = self.global_values
		for part in path:
			value = value[part]
		return value

	def save(self):
		self.save_count += 1


class FakePrinter:
	def __init__(self, completion=None, printing=False, temperatures=None, print_time=60, print_time_left=60):
		self.printing = printing
		self.temperatures = temperatures or {}
		self.current_data = {
			"progress": {
				"completion": completion,
				"printTime": print_time,
				"printTimeLeft": print_time_left,
			}
		}

	def get_current_data(self):
		return self.current_data

	def get_current_temperatures(self):
		return self.temperatures

	def is_printing(self):
		return self.printing


@pytest.fixture
def plugin_manager():
	return SimpleNamespace(plugins={})


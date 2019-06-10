import time


class MMUAssistance:

	def __init__(self, logger):
		self._logger = logger
		self._mmu_lines_skipped = None
		self._last_notification = None  # Keep track of when was user alerted last time. Helps avoid spamming

	def process_gcode(self, line):
		# MMU user assistance detection
		# Firmware will use 2 different lines to indicate the there is an MMU issue
		# and user assistance is required. There could be other lines present in the
		# terminal between the 2 relevant lines
		if line.startswith("mmu_get_response - begin move: T-code"):
			self._mmu_lines_skipped = 0
		else:
			if self._mmu_lines_skipped is not None:
				if self._mmu_lines_skipped > 5:
					# We give up waiting for the second line to be detected. False alert.
					# Reset counter
					self._mmu_lines_skipped = None
				elif line.startswith("mmu_get_response() returning: 0"):
					# Check if we never alerted or 1 minute has passed since last alert
					if self._last_notification is None or (time.time() - self._last_notification) / 60 > 1:
						self._logger.info("*** MMU Requires User Assistance ***")
						self._last_notification = time.time()
					# Second line found, reset counter now
					self._mmu_lines_skipped = None
				else:
					self._mmu_lines_skipped += 1

		# Always return what we parsed
		return line

from queue import Full, Queue
from threading import Event, Lock, Thread


class NotificationWorker:
	"""Deliver notifications without waiting on network I/O in communication hooks."""

	def __init__(self, logger, max_pending=20):
		self._logger = logger
		self._queue = Queue(maxsize=max_pending)
		self._lock = Lock()
		self._stopped = Event()
		self._thread = None

	def submit(self, callback, *args):
		# Bound the backlog and never wait for a slow notification to finish.
		with self._lock:
			if self._stopped.is_set():
				return False
			if self._thread is None:
				self._thread = Thread(target=self._run, name="OctoPodNotifications", daemon=True)
				self._thread.start()
			try:
				self._queue.put_nowait((callback, args))
			except Full:
				self._logger.warning("Notification queue full; skipping notification")
				return False
		return True

	def shutdown(self):
		# Pending notifications are discarded. An in-flight request may finish,
		# but must not delay OctoPrint shutdown.
		with self._lock:
			if self._stopped.is_set():
				return
			self._stopped.set()
			try:
				self._queue.put_nowait(None)
			except Full:
				pass

	def _run(self):
		while not self._stopped.is_set():
			job = self._queue.get()
			try:
				if job is None or self._stopped.is_set():
					return
				callback, args = job
				callback(*args)
			except Exception:
				self._logger.exception("Error delivering notification")
			finally:
				self._queue.task_done()

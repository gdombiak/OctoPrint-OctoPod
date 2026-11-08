from threading import Event
from unittest.mock import Mock

from octoprint_octopod.notification_worker import NotificationWorker

from conftest import wait_for_notifications


def test_worker_continues_after_a_delivery_exception(notification_worker):
	failed = Mock(side_effect=RuntimeError("Delivery failed"))
	delivered = Mock()

	assert notification_worker.submit(failed)
	assert notification_worker.submit(delivered, "next notification")
	wait_for_notifications(notification_worker)

	failed.assert_called_once_with()
	delivered.assert_called_once_with("next notification")
	notification_worker._logger.exception.assert_called_once()


def test_full_queue_drops_work_without_waiting_for_delivery():
	worker = NotificationWorker(Mock(), max_pending=1)
	started, release, finished = Event(), Event(), Event()
	skipped = Mock()

	def blocked():
		started.set()
		assert release.wait(5)

	try:
		assert worker.submit(blocked)
		assert started.wait(2)
		assert worker.submit(finished.set)
		assert not worker.submit(skipped)
		worker._logger.warning.assert_called_once()
		release.set()
		assert finished.wait(2)
		skipped.assert_not_called()
	finally:
		release.set()
		worker.shutdown()
		worker._thread.join(timeout=2)
		assert not worker._thread.is_alive()


def test_shutdown_does_not_wait_for_inflight_request_or_deliver_pending_work(notification_worker):
	started, release = Event(), Event()
	pending = Mock()

	def blocked():
		started.set()
		assert release.wait(5)

	try:
		assert notification_worker.submit(blocked)
		assert started.wait(2)
		assert notification_worker.submit(pending)
		notification_worker.shutdown()
		assert not notification_worker.submit(pending)
		assert notification_worker._thread.is_alive()
	finally:
		release.set()
		notification_worker._thread.join(timeout=2)

	pending.assert_not_called()
	assert not notification_worker._thread.is_alive()


def test_shutdown_before_first_notification_does_not_start_a_thread(notification_worker):
	notification_worker.shutdown()
	assert not notification_worker.submit(Mock())
	assert notification_worker._thread is None

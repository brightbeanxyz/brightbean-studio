"""Tests for the spawned-thread connection helpers."""

from unittest.mock import patch

from django.db import connections
from django.test import TestCase, TransactionTestCase

from apps.common.db import in_worker_thread, release_idle_connection


def _raise():
    raise ValueError("boom")


class InWorkerThreadTests(TestCase):
    def test_returns_the_wrapped_return_value(self):
        self.assertEqual(in_worker_thread(lambda a, b=0: a + b, 1, b=2), 3)

    def test_closes_connections_when_the_body_succeeds(self):
        with patch.object(connections, "close_all") as close_all:
            in_worker_thread(lambda: None)

        close_all.assert_called_once()

    def test_closes_connections_when_the_body_raises(self):
        # The failing path is the one that matters: a publish that raises is
        # exactly when a leaked connection goes unnoticed, and the publisher
        # logs these rather than letting them stop the cycle.
        with patch.object(connections, "close_all") as close_all, self.assertRaises(ValueError):
            in_worker_thread(_raise)

        close_all.assert_called_once()


class ReleaseIdleConnectionTests(TransactionTestCase):
    """Uses TransactionTestCase so ``in_atomic_block`` reflects real state.

    A plain ``TestCase`` wraps every test in an atomic block, which would make
    the "not in a transaction" case untestable — and is itself the scenario the
    atomic-block guard exists for.
    """

    def test_closes_an_idle_connection(self):
        connections["default"].ensure_connection()
        self.assertIsNotNone(connections["default"].connection)

        release_idle_connection()

        self.assertIsNone(connections["default"].connection)

    def test_leaves_a_connection_inside_a_transaction_alone(self):
        # Django's close() does not refuse inside an atomic block: it flags the
        # connection needs_rollback and closed_in_transaction, silently dooming
        # the caller's transaction. Closing here has to be skipped, not merely
        # survive.
        from django.db import transaction

        with transaction.atomic():
            connections["default"].ensure_connection()

            release_idle_connection()

            self.assertFalse(connections["default"].needs_rollback)
            self.assertFalse(connections["default"].closed_in_transaction)
            # And the transaction is still usable.
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                self.assertEqual(cursor.fetchone()[0], 1)

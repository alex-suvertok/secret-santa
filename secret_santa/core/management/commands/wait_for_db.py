from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, connections


class Command(BaseCommand):
    """Wait for the database to become reachable before starting the app."""

    help = "Wait for the database to be available (used at container startup)."

    def handle(self, *args, **options):
        connection = connections["default"]
        for attempt in range(1, 31):
            try:
                connection.close()
                connection.ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database is available."))
                return
            except OperationalError as exc:
                self.stdout.write(
                    f"Database not ready (attempt {attempt}/30): {exc}. Retrying in 2s..."
                )
                sleep(2)
        raise CommandError("Database did not become available in time.")
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a superuser from environment variables"

    def handle(self, *args, **options):
        username = os.getenv("SUPERUSERNAME")
        password = os.getenv("SUPERPASSWORD")

        if not username:
            raise CommandError("SUPERUSERNAME is not set")

        if not password:
            raise CommandError("SUPERPASSWORD is not set")

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser '{username}' already exists."
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{username}' created successfully."
            )
        )
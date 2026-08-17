from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create a Django superuser using username and password arguments"

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Username for the superuser",
        )
        parser.add_argument(
            "password",
            type=str,
            help="Password for the superuser",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        username = options["username"]
        password = options["password"]

        if User.objects.filter(email=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser '{username}' already exists."
                )
            )
            return

        user = User.objects.create_superuser(
            password=password,
            email=username,
        )
        user.username = username
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{user.username}' created successfully."
            )
        )
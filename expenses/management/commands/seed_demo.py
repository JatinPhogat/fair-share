from datetime import date

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from expenses.models import Group, GroupMembership

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo group with flatmates from the assignment"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            email="demo@fairshare.app",
            defaults={"username": "demo", "is_staff": True},
        )
        if created:
            user.set_password("demo1234")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created demo user (demo@fairshare.app / demo1234)"))

        group, created = Group.objects.get_or_create(
            name="Flat 4B",
            defaults={"description": "Shared flat expenses", "created_by": user},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created group: {group.name}"))

        members = [
            {"display_name": "Aisha", "joined_at": date(2026, 2, 1), "left_at": None},
            {"display_name": "Rohan", "joined_at": date(2026, 2, 1), "left_at": None},
            {"display_name": "Priya", "joined_at": date(2026, 2, 1), "left_at": None},
            {"display_name": "Meera", "joined_at": date(2026, 2, 1), "left_at": date(2026, 3, 31)},
            {"display_name": "Dev", "joined_at": date(2026, 2, 8), "left_at": None},
            {"display_name": "Sam", "joined_at": date(2026, 4, 8), "left_at": None},
        ]

        for m in members:
            obj, created = GroupMembership.objects.get_or_create(
                group=group,
                display_name=m["display_name"],
                defaults={"joined_at": m["joined_at"], "left_at": m["left_at"]},
            )
            if created:
                self.stdout.write(f"  Added member: {m['display_name']}")

        self.stdout.write(self.style.SUCCESS(
            "\nDemo ready! Login with demo@fairshare.app / demo1234"
            f"\nGroup '{group.name}' (id={group.id}) has {group.memberships.count()} members"
            "\nUpload the CSV via the import feature to populate expenses."
        ))

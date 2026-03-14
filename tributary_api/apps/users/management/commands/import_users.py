"""
Import users from a CSV file.

CSV columns (header row required):
    email, first_name, last_name, password, bio, district_nces_id

Only `email` and `password` are required. All other columns are optional.

Usage:
    python manage.py import_users users.csv
    python manage.py import_users users.csv --default-password DemoPass123
    python manage.py import_users users.csv --dry-run
"""
import csv

from django.core.management.base import BaseCommand

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.users.models import FerpaConsent, User


class Command(BaseCommand):
    help = "Import users from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "file", type=str,
            help="Path to the CSV file",
        )
        parser.add_argument(
            "--default-password", type=str, default="",
            help="Password to use when the CSV row has no password column or value",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Validate the CSV without creating any users",
        )
        parser.add_argument(
            "--skip-existing", action="store_true",
            help="Skip rows whose email already exists instead of erroring",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        default_password = options["default_password"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]

        try:
            with open(file_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        if not rows:
            self.stdout.write(self.style.ERROR("CSV file is empty."))
            return

        # Validate required column
        headers = rows[0].keys()
        if "email" not in headers:
            self.stdout.write(self.style.ERROR(
                f"CSV must have an 'email' column. Found: {', '.join(headers)}"
            ))
            return

        has_password_col = "password" in headers
        if not has_password_col and not default_password:
            self.stdout.write(self.style.ERROR(
                "CSV has no 'password' column and no --default-password provided."
            ))
            return

        # Cache districts by NCES ID for lookup
        district_cache = {}

        self.stdout.write(f"Processing {len(rows)} rows from {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no users will be created"))

        created = 0
        skipped = 0
        errors = 0

        for i, row in enumerate(rows, start=2):  # start=2 because row 1 is header
            email = row.get("email", "").strip().lower()
            if not email:
                self.stdout.write(self.style.ERROR(f"  Row {i}: missing email — skipped"))
                errors += 1
                continue

            # Check for existing user
            if User.objects.filter(email=email).exists():
                if skip_existing:
                    self.stdout.write(f"  Row {i}: {email} already exists — skipped")
                    skipped += 1
                    continue
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  Row {i}: {email} already exists (use --skip-existing to skip)"
                    ))
                    errors += 1
                    continue

            password = row.get("password", "").strip() or default_password
            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            bio = row.get("bio", "").strip()
            nces_id = row.get("district_nces_id", "").strip()

            # Resolve district
            district = None
            if nces_id:
                if nces_id not in district_cache:
                    district_cache[nces_id] = District.objects.filter(nces_id=nces_id).first()
                district = district_cache[nces_id]
                if not district:
                    self.stdout.write(self.style.WARNING(
                        f"  Row {i}: district NCES ID '{nces_id}' not found — user created without district"
                    ))

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f"  Row {i}: {email} — {first_name} {last_name} — OK"
                ))
                created += 1
                continue

            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role="MEMBER",
                is_active=True,
                bio=bio,
                district=district,
            )

            # Email verification
            EmailAddress.objects.create(
                user=user, email=email, primary=True, verified=True,
            )

            # FERPA consent
            FerpaConsent.objects.create(
                user=user, ip_address="127.0.0.1", consent_text_version="1.0",
            )

            created += 1
            self.stdout.write(f"  Row {i}: {email} — created")

        self.stdout.write("")
        self.stdout.write("=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN SUMMARY"))
        else:
            self.stdout.write(self.style.SUCCESS("IMPORT COMPLETE"))
        self.stdout.write(f"  Created:  {created}")
        self.stdout.write(f"  Skipped:  {skipped}")
        self.stdout.write(f"  Errors:   {errors}")
        self.stdout.write("=" * 50)

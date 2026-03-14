from django.core.management.base import BaseCommand

from etl.ingest_nces import run_ingestion


class Command(BaseCommand):
    help = "Ingest NCES CCD district data into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to a local CSV file. If omitted, downloads from NCES.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would be done without writing to DB.",
        )
        parser.add_argument(
            "--vintage",
            type=str,
            default="2024-25",
            help="Data vintage string, e.g. '2022-23'.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting NCES CCD ETL...")
        try:
            result = run_ingestion(
                local_file=options["file"],
                dry_run=options["dry_run"],
                data_vintage=options["vintage"],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: {result['added']} added, {result['updated']} updated, "
                    f"{result['skipped']} skipped, {result['errors']} errors."
                )
            )
        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))

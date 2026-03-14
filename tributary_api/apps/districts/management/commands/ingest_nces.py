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
            "--url",
            type=str,
            default=None,
            help="URL to download a CSV file from (e.g. a GitHub raw link).",
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

        # If --url is provided, download to a temp file first
        local_file = options["file"]
        if options["url"]:
            import tempfile
            import urllib.request
            self.stdout.write(f"Downloading from {options['url']}...")
            tmp = tempfile.NamedTemporaryFile(
                suffix=".csv", delete=False, mode="wb"
            )
            try:
                urllib.request.urlretrieve(options["url"], tmp.name)
                local_file = tmp.name
                self.stdout.write(f"Downloaded to {tmp.name}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Download failed: {e}"))
                return

        try:
            result = run_ingestion(
                local_file=local_file,
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

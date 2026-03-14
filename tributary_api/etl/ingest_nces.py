"""
NCES CCD ETL Script for TRIBUTARY.

Supports two CSV formats:
  1. Raw NCES CCD files (columns: LEAID, LEA_NAME, STABR, ULOCALE, MEMBER, etc.)
  2. ELSI Table Generator exports (columns: Agency Name, State Name, Locale, etc.)

NCES locale code -> locale_type mapping:
    NCES codes 11, 12, 13 (City - Large, Midsize, Small)       -> URBAN
    NCES codes 21, 22, 23 (Suburb - Large, Midsize, Small)     -> SUBURBAN
    NCES codes 31, 32, 33 (Town - Fringe, Distant, Remote)     -> TOWN
    NCES codes 41, 42, 43 (Rural - Fringe, Distant, Remote)    -> RURAL

Invocation modes:
    Management command: python manage.py ingest_nces [--file path.csv] [--dry-run]
    Celery task:        from etl.ingest_nces import run_ingestion; run_ingestion()
"""
import csv
import io
import logging
import os
import re
import urllib.request
from decimal import Decimal, InvalidOperation

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tributary_api.settings.dev")

logger = logging.getLogger(__name__)

NCES_LOCALE_MAP = {
    "11": "URBAN", "12": "URBAN", "13": "URBAN",
    "21": "SUBURBAN", "22": "SUBURBAN", "23": "SUBURBAN",
    "31": "TOWN", "32": "TOWN", "33": "TOWN",
    "41": "RURAL", "42": "RURAL", "43": "RURAL",
}

# US state name -> abbreviation mapping for ELSI exports
STATE_ABBREVS = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI",
    "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME",
    "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE",
    "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM",
    "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX",
    "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "AMERICAN SAMOA": "AS", "GUAM": "GU", "NORTHERN MARIANA ISLANDS": "MP",
    "PUERTO RICO": "PR", "U.S. VIRGIN ISLANDS": "VI",
}

# NCES CCD directory data URL — update when new vintage is released
NCES_CCD_URL = (
    "https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2223_w_1a_071524.zip"
)

# Column name mappings for raw NCES CCD files.
COLUMN_ALIASES = {
    "LEAID": ["LEAID", "LEA_ID", "NCESSCH"],
    "NAME": ["LEA_NAME", "NAME", "SCHNAM", "AGENCY_NAME"],
    "STATE": ["STATE_NAME", "STABR", "ST", "LSTATE", "FIPST"],
    "ULOCALE": ["ULOCALE", "LOCALE", "ULOCAL"],
    "MEMBER": ["MEMBER", "TOTAL", "ENROLLMENT", "TOTALENROLLMENT"],
    "FRELCH": ["FRELCH", "FREE_LUNCH", "TOTFRL"],
    "REDLCH": ["REDLCH", "REDUCED_LUNCH"],
    "ELL": ["ELL", "LEP", "ENGLISH_LEARNER", "TOTAL_ELL"],
}


def _resolve_column(headers, field_name):
    """Find actual column name from aliases."""
    for alias in COLUMN_ALIASES.get(field_name, [field_name]):
        if alias in headers:
            return alias
    return None


def _safe_int(value, default=0):
    """Parse a value as integer, returning default on failure."""
    if value is None:
        return default
    value = str(value).strip()
    if value in ("", ".", "-", "N", "M", "–", "†", "‡"):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _safe_decimal(value, default=Decimal("0.00")):
    """Parse a value as Decimal, returning default on failure."""
    if value is None:
        return default
    value = str(value).strip()
    if value in ("", ".", "-", "N", "M", "–", "†", "‡"):
        return default
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _state_abbrev(raw_state):
    """Convert a state name or abbreviation to a 2-letter abbreviation."""
    raw = raw_state.strip()
    # Already an abbreviation
    if len(raw) <= 2:
        return raw.upper()
    # Look up full name
    abbrev = STATE_ABBREVS.get(raw.upper())
    if abbrev:
        return abbrev
    # Fallback: take first 2 chars
    return raw[:2].upper()


def _extract_locale_code(locale_str):
    """Extract the 2-digit locale code from ELSI format like '21-Suburb: Large'."""
    if not locale_str:
        return None
    match = re.match(r"(\d{2})", locale_str.strip())
    return match.group(1) if match else None


def _detect_elsi_format(content):
    """Detect if the CSV is an ELSI Table Generator export.

    ELSI exports start with 'ELSI Export' on line 1, followed by metadata,
    with the actual header row containing 'Agency Name'.
    """
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "Agency Name" in line or "Agency ID" in line:
            return True, i
    return False, 0


def _find_elsi_column(headers, *keywords):
    """Find an ELSI column header containing all given keywords (case-insensitive)."""
    for h in headers:
        h_lower = h.lower()
        if all(kw.lower() in h_lower for kw in keywords):
            return h
    return None


def run_ingestion(local_file=None, dry_run=False, data_vintage="2024-25"):
    """
    Run the NCES CCD ETL process.

    Args:
        local_file: Path to a local CSV file. If None, downloads from NCES.
        dry_run: If True, prints what would be done without writing to DB.
        data_vintage: The data vintage string, e.g. "2024-25".
    """
    django.setup()
    from apps.districts.models import District

    added = 0
    updated = 0
    skipped = 0
    errors = 0

    # Get CSV data
    if local_file:
        if not os.path.exists(local_file):
            raise ValueError(f"File not found: {local_file}.")
        with open(local_file, "r", encoding="utf-8-sig") as f:
            content = f.read()
    else:
        try:
            logger.info("Downloading NCES CCD data...")
            if NCES_CCD_URL.endswith(".zip"):
                import zipfile
                response = urllib.request.urlopen(NCES_CCD_URL)
                zip_data = io.BytesIO(response.read())
                with zipfile.ZipFile(zip_data) as zf:
                    csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
                    if not csv_files:
                        raise ValueError("No CSV file found in NCES ZIP archive.")
                    with zf.open(csv_files[0]) as csv_file:
                        content = csv_file.read().decode("utf-8-sig")
            else:
                response = urllib.request.urlopen(NCES_CCD_URL)
                content = response.read().decode("utf-8-sig")
        except Exception as e:
            raise ValueError(
                f"Failed to download NCES data: {e}. "
                "Use --file to provide a local CSV instead."
            )

    # Detect format
    is_elsi, header_line = _detect_elsi_format(content)

    if is_elsi:
        return _ingest_elsi(content, header_line, dry_run, data_vintage)
    else:
        return _ingest_raw_ccd(content, dry_run, data_vintage)


def _ingest_elsi(content, header_line, dry_run, data_vintage):
    """Ingest from an ELSI Table Generator CSV export."""
    from apps.districts.models import District

    added = 0
    updated = 0
    skipped = 0
    errors = 0

    # Skip preamble lines
    lines = content.split("\n")
    csv_content = "\n".join(lines[header_line:])

    reader = csv.DictReader(io.StringIO(csv_content))
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

    headers = reader.fieldnames or []
    logger.info(f"ELSI columns detected: {headers}")

    # Resolve ELSI column names
    col_leaid = _find_elsi_column(headers, "Agency ID")
    col_name = _find_elsi_column(headers, "Agency Name")
    col_state = _find_elsi_column(headers, "State")
    col_locale = _find_elsi_column(headers, "Locale")
    col_enrollment = _find_elsi_column(headers, "Total Students")
    col_frl = _find_elsi_column(headers, "Free Lunch") or _find_elsi_column(headers, "Lunch")
    col_redlch = _find_elsi_column(headers, "Reduced")
    col_ell = _find_elsi_column(headers, "English Language") or _find_elsi_column(headers, "ELL")

    missing = []
    for field, col in [
        ("Agency ID", col_leaid), ("Agency Name", col_name),
        ("State", col_state), ("Locale", col_locale),
    ]:
        if col is None:
            missing.append(field)

    if missing:
        raise ValueError(
            f"Missing required ELSI columns: {missing}. "
            f"Available columns: {headers}"
        )

    logger.info(
        f"ELSI column mapping: LEAID={col_leaid}, NAME={col_name}, "
        f"STATE={col_state}, LOCALE={col_locale}, ENROLLMENT={col_enrollment}, "
        f"FRL={col_frl}, REDLCH={col_redlch}, ELL={col_ell}"
    )

    for row in reader:
        leaid = (row.get(col_leaid) or "").strip()

        # Skip non-data rows (footer notes, empty)
        if not leaid or not leaid.isdigit():
            skipped += 1
            continue

        # Extract locale code from ELSI format "21-Suburb: Large"
        raw_locale = (row.get(col_locale) or "").strip()
        locale_code = _extract_locale_code(raw_locale)
        if locale_code is None:
            logger.warning(f"Unknown locale '{raw_locale}' for LEAID {leaid}, skipping.")
            skipped += 1
            continue

        locale_type = NCES_LOCALE_MAP.get(locale_code)
        if locale_type is None:
            logger.warning(f"Unknown locale code '{locale_code}' for LEAID {leaid}, skipping.")
            skipped += 1
            continue

        name = (row.get(col_name) or "").strip()
        state = _state_abbrev(row.get(col_state) or "")
        member = _safe_int(row.get(col_enrollment)) if col_enrollment else 0

        # FRL percentage
        frelch = _safe_int(row.get(col_frl)) if col_frl else 0
        redlch = _safe_int(row.get(col_redlch)) if col_redlch else 0
        if member > 0 and (frelch + redlch) > 0:
            frl_pct = Decimal(str(round((frelch + redlch) / member * 100, 2)))
        else:
            frl_pct = Decimal("0.00")

        # ELL percentage
        ell = _safe_int(row.get(col_ell)) if col_ell else 0
        if member > 0 and ell > 0:
            ell_pct = Decimal(str(round(ell / member * 100, 2)))
        else:
            ell_pct = Decimal("0.00")

        if dry_run:
            print(
                f"[DRY RUN] Would upsert: {leaid} — {name} ({state}) "
                f"locale={locale_type} enroll={member} frl={frl_pct}% ell={ell_pct}%"
            )
            added += 1
            continue

        try:
            _, created = District.objects.update_or_create(
                nces_id=leaid,
                defaults={
                    "name": name,
                    "state": state,
                    "locale_type": locale_type,
                    "enrollment": member,
                    "frl_pct": frl_pct,
                    "ell_pct": ell_pct,
                    "data_vintage": data_vintage,
                },
            )
            if created:
                added += 1
            else:
                updated += 1
        except Exception as e:
            logger.error(f"Error upserting LEAID {leaid}: {e}")
            errors += 1

    summary = (
        f"NCES ETL complete (ELSI format): {added} added, {updated} updated, "
        f"{skipped} skipped, {errors} errors."
    )
    print(summary)
    logger.info(summary)

    return {"added": added, "updated": updated, "skipped": skipped, "errors": errors}


def _ingest_raw_ccd(content, dry_run, data_vintage):
    """Ingest from a raw NCES CCD CSV file."""
    from apps.districts.models import District

    added = 0
    updated = 0
    skipped = 0
    errors = 0

    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

    headers = set(reader.fieldnames or [])

    col_leaid = _resolve_column(headers, "LEAID")
    col_name = _resolve_column(headers, "NAME")
    col_state = _resolve_column(headers, "STATE")
    col_ulocale = _resolve_column(headers, "ULOCALE")
    col_member = _resolve_column(headers, "MEMBER")
    col_frelch = _resolve_column(headers, "FRELCH")
    col_redlch = _resolve_column(headers, "REDLCH")
    col_ell = _resolve_column(headers, "ELL")

    missing = []
    for field, col in [
        ("LEAID", col_leaid), ("NAME", col_name), ("STATE", col_state),
        ("ULOCALE", col_ulocale), ("MEMBER", col_member),
    ]:
        if col is None:
            missing.append(field)

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {sorted(headers)}. "
            "NCES column names may have changed — check devlog.md."
        )

    logger.info(
        f"Column mapping: LEAID={col_leaid}, NAME={col_name}, "
        f"STATE={col_state}, ULOCALE={col_ulocale}, MEMBER={col_member}, "
        f"FRELCH={col_frelch}, REDLCH={col_redlch}, ELL={col_ell}"
    )

    for row in reader:
        leaid = (row.get(col_leaid) or "").strip()

        if not leaid or not leaid.isdigit():
            skipped += 1
            continue

        ulocale = (row.get(col_ulocale) or "").strip()
        locale_type = NCES_LOCALE_MAP.get(ulocale)
        if locale_type is None:
            logger.warning(f"Unknown ULOCALE code '{ulocale}' for LEAID {leaid}, skipping.")
            skipped += 1
            continue

        name = (row.get(col_name) or "").strip()
        state = (row.get(col_state) or "").strip()[:2].upper()
        member = _safe_int(row.get(col_member))

        frelch = _safe_int(row.get(col_frelch) if col_frelch else None)
        redlch = _safe_int(row.get(col_redlch) if col_redlch else None)
        if member > 0:
            frl_pct = Decimal(str(round((frelch + redlch) / member * 100, 2)))
        else:
            frl_pct = Decimal("0.00")

        ell = _safe_int(row.get(col_ell) if col_ell else None)
        if member > 0:
            ell_pct = Decimal(str(round(ell / member * 100, 2)))
        else:
            ell_pct = Decimal("0.00")

        if dry_run:
            print(
                f"[DRY RUN] Would upsert: {leaid} — {name} ({state}) "
                f"locale={locale_type} enroll={member} frl={frl_pct}% ell={ell_pct}%"
            )
            added += 1
            continue

        try:
            _, created = District.objects.update_or_create(
                nces_id=leaid,
                defaults={
                    "name": name,
                    "state": state,
                    "locale_type": locale_type,
                    "enrollment": member,
                    "frl_pct": frl_pct,
                    "ell_pct": ell_pct,
                    "data_vintage": data_vintage,
                },
            )
            if created:
                added += 1
            else:
                updated += 1
        except Exception as e:
            logger.error(f"Error upserting LEAID {leaid}: {e}")
            errors += 1

    summary = (
        f"NCES ETL complete: {added} added, {updated} updated, "
        f"{skipped} skipped, {errors} errors."
    )
    print(summary)
    logger.info(summary)

    return {"added": added, "updated": updated, "skipped": skipped, "errors": errors}

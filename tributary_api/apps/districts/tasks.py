from celery import shared_task


@shared_task(name="districts.ingest_nces_data")
def ingest_nces_data():
    from etl.ingest_nces import run_ingestion
    run_ingestion()

"""
IngestionService — orchestrates raw data pull from a connector and persists to DB.

Sprint 1 TODO: Implement full ingestion loop:
  1. Resolve active connector (mock / csv / shopify / …)
  2. Fetch raw records for the requested date range
  3. Validate records via ValidationService
  4. Write to raw_* tables (upsert by external_id)
  5. Record IngestionRun metadata
  6. Emit PipelineEvents for errors and warnings
"""

from datetime import date
from typing import Optional

from app.connectors.base import BaseCommerceConnector


class IngestionService:
    def __init__(self, connector: BaseCommerceConnector):
        self.connector = connector

    def run(
        self,
        start_date: date,
        end_date: date,
        dry_run: bool = False,
    ) -> dict:
        """
        Scaffold: returns a status dict indicating no data is ingested yet.
        Sprint 1 TODO: implement full ingestion and return real counts.
        """
        return {
            "status": "scaffold_ready",
            "message": "IngestionService not yet implemented — Sprint 1.",
            "connector": self.connector.connector_name,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "dry_run": dry_run,
            "records_ingested": 0,
        }

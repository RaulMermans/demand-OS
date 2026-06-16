#!/usr/bin/env python3
"""
seed_demo_data.py — Generate synthetic demo data and ingest it via MockCommerceConnector.

Sprint 1 TODO: Implement after MockCommerceConnector generates realistic data.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --dry-run
    python scripts/seed_demo_data.py --years 2 --products 50 --stores 5
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Seed DemandOS with synthetic demo data.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to DB.")
    parser.add_argument("--years", type=int, default=2, help="Years of history to generate.")
    parser.add_argument("--products", type=int, default=50, help="Number of products.")
    parser.add_argument("--stores", type=int, default=5, help="Number of stores.")
    args = parser.parse_args()

    print("DemandOS — Seed Demo Data")
    print("=" * 40)
    print(f"Config: {args.years} years, {args.products} products, {args.stores} stores")
    print()
    print("Status: NOT IMPLEMENTED — Sprint 1")
    print()
    print("Sprint 1 TODO:")
    print("  1. Implement MockCommerceConnector with synthetic data generation")
    print("  2. Implement IngestionService to persist records to DB")
    print("  3. Call IngestionService.run() here with full date range")
    print("  4. Print summary: products, stores, orders, inventory snapshots ingested")
    print()
    print("Reference: g-schumacher44/ecom_sales_data_generator for data patterns.")
    sys.exit(0)


if __name__ == "__main__":
    main()

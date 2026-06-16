"""
MockCommerceConnector — deterministic synthetic e-commerce/retail data generator.

Generates a realistic apparel-retail dataset:
  - 50 products across 5 categories (bestsellers, standard, slow-movers)
  - 5 stores/channels with different demand profiles
  - 10 suppliers with realistic lead times and reliability scores
  - 730 days of order-line history with weekday + seasonal + promotional patterns
  - 8–11 promotional events per year with demand uplift
  - Daily inventory snapshots, including real stockout events
  - Purchase orders driven by internal reorder logic (not persisted as derived fields)

Rules enforced:
  - Returns raw operational records only (no ML features, no forecasts, no risk scores)
  - Deterministic: same seed + same config always produces same IDs and records
  - Simulation internally tracks latent demand but never persists it
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time as dt_time
from typing import Optional
import math
import random

from app.connectors.base import BaseCommerceConnector
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
)

CONNECTOR_NAME = "mock"

_CATEGORIES = [
    ("Tops", "T-Shirts"),
    ("Tops", "Sweaters"),
    ("Bottoms", "Jeans"),
    ("Bottoms", "Trousers"),
    ("Footwear", "Sneakers"),
    ("Footwear", "Boots"),
    ("Accessories", "Belts"),
    ("Accessories", "Bags"),
    ("Outerwear", "Jackets"),
    ("Outerwear", "Coats"),
]

_PRODUCT_ADJECTIVES = [
    "Classic", "Premium", "Urban", "Street", "Slim", "Relaxed",
    "Heritage", "Essential", "Luxe", "Modern", "Vintage", "Casual",
    "Sport", "Active", "Elevated", "Basic", "Core", "Signature",
    "Bold", "Refined",
]

# Static store definitions (first N used based on store_count)
_STORE_DEFS = [
    dict(id="store_001", name="Online Store",           channel="online",    region="ES", country="ES", tz="Europe/Madrid", dm=2.5),
    dict(id="store_002", name="Madrid Flagship",        channel="retail",    region="Madrid",    country="ES", tz="Europe/Madrid", dm=1.0),
    dict(id="store_003", name="Barcelona Store",        channel="retail",    region="Catalonia", country="ES", tz="Europe/Madrid", dm=0.8),
    dict(id="store_004", name="Outlet",                 channel="outlet",    region="ES", country="ES", tz="Europe/Madrid", dm=0.5),
    dict(id="store_005", name="Wholesale/Marketplace",  channel="wholesale", region="EU", country="EU", tz="Europe/Madrid", dm=1.8),
]

_SUPPLIER_DEFS = [
    dict(name="Textiles Barcelona SA",  country="ES", lt_min=7,  lt_max=14, rel=0.97),
    dict(name="Moda Portugal Lda",      country="PT", lt_min=10, lt_max=18, rel=0.94),
    dict(name="Milano Fabrics SRL",     country="IT", lt_min=14, lt_max=21, rel=0.96),
    dict(name="BerlinMade GmbH",        country="DE", lt_min=12, lt_max=20, rel=0.93),
    dict(name="Shanghai Textile Co",    country="CN", lt_min=28, lt_max=45, rel=0.88),
    dict(name="Hanoi Garments Ltd",     country="VN", lt_min=30, lt_max=42, rel=0.85),
    dict(name="Delhi Fashion Pvt",      country="IN", lt_min=25, lt_max=38, rel=0.82),
    dict(name="Istanbul Style AS",      country="TR", lt_min=14, lt_max=22, rel=0.91),
    dict(name="London Brands Ltd",      country="GB", lt_min=8,  lt_max=16, rel=0.98),
    dict(name="Amsterdam Trade BV",     country="NL", lt_min=6,  lt_max=12, rel=0.99),
]

# Retail price ranges per category: (min_price, max_price, min_markup, max_markup)
_PRICE_BANDS: dict[str, tuple[float, float, float, float]] = {
    "Tops":        (12.0,  55.0,  2.0, 3.2),
    "Bottoms":     (25.0,  95.0,  2.2, 3.5),
    "Footwear":    (45.0, 185.0,  2.5, 3.8),
    "Accessories": (10.0,  65.0,  2.8, 4.0),
    "Outerwear":   (65.0, 230.0,  2.2, 3.2),
}

# Monthly demand multipliers (1 = Jan … 12 = Dec)
_MONTH_FACTOR: dict[int, float] = {
    1: 0.70, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.10, 6: 1.00,
    7: 1.30, 8: 1.20, 9: 0.90, 10: 1.00, 11: 1.50, 12: 2.00,
}

# Day-of-week multipliers (0 = Mon … 6 = Sun)
_DOW_FACTOR: dict[int, float] = {
    0: 0.90, 1: 0.80, 2: 0.90, 3: 1.00, 4: 1.30, 5: 1.40, 6: 0.70,
}

# Promotion templates: (label, month, day_start, day_end, discount_pct, promo_type, cat_filter)
_PROMO_TEMPLATES = [
    ("New Year Sale",       1,  1,  7,  0.20, "discount",   None),
    ("Valentine's Day",     2, 10, 14,  0.15, "discount",   "Accessories"),
    ("Spring Collection",   3, 20, 31,  0.15, "discount",   None),
    ("Summer Pre-Sale",     6, 15, 30,  0.10, "discount",   None),
    ("Summer Sale",         7,  1, 31,  0.25, "discount",   None),
    ("Back to School",      8, 15, 31,  0.15, "discount",   "Tops"),
    ("Autumn Launch",       9,  1, 15,  0.10, "discount",   None),
    ("Black Friday",       11, 25, 30,  0.35, "flash_sale", None),
    ("Cyber Monday",       12,  1,  2,  0.30, "flash_sale", None),
    ("Christmas Sale",     12,  8, 24,  0.20, "discount",   None),
    ("Winter Sale",        12, 26, 31,  0.30, "discount",   None),
]

_MONTH_LAST_DAY = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}


@dataclass
class MockConfig:
    seed: int = 42
    product_count: int = 50
    store_count: int = 5
    history_days: int = 730
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currency: str = "EUR"

    def resolved_dates(self) -> tuple[date, date]:
        end = self.end_date or (date.today() - timedelta(days=1))
        start = self.start_date or (end - timedelta(days=self.history_days - 1))
        return start, end


class MockCommerceConnector(BaseCommerceConnector):
    """
    Deterministic synthetic e-commerce data generator for demo/testing.

    Same seed + same config always produces identical IDs and records.
    Generation happens once at construction; fetch_* methods filter the in-memory results.
    """

    connector_name = CONNECTOR_NAME

    def __init__(self, config: Optional[MockConfig] = None) -> None:
        self.config = config or MockConfig()
        self._rng = random.Random(self.config.seed)
        self._start_date, self._end_date = self.config.resolved_dates()

        # Build static catalog (order matters: suppliers first, then products)
        self._suppliers: list[RawSupplier] = self._build_suppliers()
        self._stores: list[RawStore]       = self._build_stores()
        self._products: list[RawProduct]   = self._build_products()
        self._promotions: list[RawPromotion] = self._build_promotions()

        # Run temporal simulation
        self._orders: list[RawOrderLine]           = []
        self._inventory: list[RawInventorySnapshot] = []
        self._purchase_orders: list[RawPurchaseOrder] = []
        self._run_simulation()

    # ------------------------------------------------------------------
    # Public fetch interface
    # ------------------------------------------------------------------

    def fetch_products(self) -> list[RawProduct]:
        return list(self._products)

    def fetch_stores(self) -> list[RawStore]:
        return list(self._stores)

    def fetch_suppliers(self) -> list[RawSupplier]:
        return list(self._suppliers)

    def fetch_promotions(self, start_date: date, end_date: date) -> list[RawPromotion]:
        return [
            p for p in self._promotions
            if p.start_date is not None
            and p.end_date is not None
            and p.start_date <= end_date
            and p.end_date >= start_date
        ]

    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        return [o for o in self._orders if start_date <= o.order_date <= end_date]

    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        return [s for s in self._inventory if start_date <= s.snapshot_date <= end_date]

    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        return [
            po for po in self._purchase_orders
            if po.ordered_at.date() <= end_date
            and (po.expected_delivery_date is None or po.expected_delivery_date >= start_date)
        ]

    # ------------------------------------------------------------------
    # Catalog builders
    # ------------------------------------------------------------------

    def _build_suppliers(self) -> list[RawSupplier]:
        result = []
        for i, s in enumerate(_SUPPLIER_DEFS):
            slug = s["name"].lower().replace(" ", "").replace(",", "")[:18]
            result.append(RawSupplier(
                id=f"sup_{i+1:03d}",
                external_id=f"EXT-SUP-{i+1:03d}",
                name=s["name"],
                country=s["country"],
                lead_time_days_min=s["lt_min"],
                lead_time_days_max=s["lt_max"],
                reliability_score=s["rel"],
                contact_email=f"orders@{slug}.com",
                source_connector=CONNECTOR_NAME,
            ))
        return result

    def _build_stores(self) -> list[RawStore]:
        result = []
        for d in _STORE_DEFS[: self.config.store_count]:
            result.append(RawStore(
                id=d["id"],
                external_id=f"EXT-{d['id'].upper()}",
                name=d["name"],
                region=d["region"],
                country=d["country"],
                timezone=d["tz"],
                channel=d["channel"],
                is_active=True,
                source_connector=CONNECTOR_NAME,
            ))
        return result

    def _build_products(self) -> list[RawProduct]:
        n = self.config.product_count
        cats = (_CATEGORIES * ((n // len(_CATEGORIES)) + 1))[:n]
        adjs = (_PRODUCT_ADJECTIVES * ((n // len(_PRODUCT_ADJECTIVES)) + 1))[:n]
        n_sup = len(self._suppliers)

        result = []
        for i in range(n):
            # Tier: 20% bestseller, 60% standard, 20% slow_mover
            tier_ratio = i / max(n - 1, 1)
            if tier_ratio < 0.20:
                tier = "bestseller"
            elif tier_ratio < 0.80:
                tier = "standard"
            else:
                tier = "slow_mover"

            cat, subcat = cats[i]
            p_min, p_max, m_min, m_max = _PRICE_BANDS.get(cat, (15.0, 80.0, 2.0, 3.0))
            retail_price = round(self._rng.uniform(p_min, p_max), 2)
            markup = self._rng.uniform(m_min, m_max)
            unit_cost = round(retail_price / markup, 2)

            supplier = self._suppliers[(i * n_sup) // n]
            lt = self._rng.randint(supplier.lead_time_days_min or 7, supplier.lead_time_days_max or 21)

            # Launch date: spread within history window; guard against tiny history_days
            lo = min(10, max(0, self.config.history_days // 4))
            hi = max(lo + 1, self.config.history_days - lo)
            days_back = self._rng.randint(lo, hi)
            launch_date = self._end_date - timedelta(days=days_back)

            result.append(RawProduct(
                id=f"prod_{i+1:03d}",
                external_id=f"EXT-PROD-{i+1:03d}",
                sku=f"SKU-{cat[:3].upper()}-{i+1:03d}",
                name=f"{adjs[i]} {subcat}",
                category=cat,
                brand="DemandBrand",
                supplier_id=supplier.id,
                unit_cost=unit_cost,
                unit_price=retail_price,
                lead_time_days=lt,
                is_active=True,
                attributes={
                    "tier": tier,
                    "subcategory": subcat,
                    "launch_date": str(launch_date),
                },
                source_connector=CONNECTOR_NAME,
            ))
        return result

    def _build_promotions(self) -> list[RawPromotion]:
        all_store_ids = [s.id for s in self._stores]
        promos: list[RawPromotion] = []
        promo_counter = 0

        for year in range(self._start_date.year, self._end_date.year + 1):
            for label, month, d_start, d_end, discount, ptype, cat_filter in _PROMO_TEMPLATES:
                # Clamp end day to valid month day
                max_day = _MONTH_LAST_DAY.get(month, 30)
                if year % 4 == 0 and month == 2:
                    max_day = 29  # leap year
                d_end_clamped = min(d_end, max_day)

                try:
                    promo_start = date(year, month, d_start)
                    promo_end   = date(year, month, d_end_clamped)
                except ValueError:
                    continue

                # Skip if entirely outside our history window
                if promo_end < self._start_date or promo_start > self._end_date:
                    continue

                applicable_skus: list[str] = []
                if cat_filter:
                    applicable_skus = [p.sku for p in self._products if p.category == cat_filter]

                promo_counter += 1
                promos.append(RawPromotion(
                    id=f"promo_{year}_{promo_counter:04d}",
                    external_id=f"EXT-PROMO-{year}-{promo_counter:04d}",
                    name=f"{year} {label}",
                    promotion_type=ptype,
                    discount_pct=discount,
                    start_date=promo_start,
                    end_date=promo_end,
                    applicable_skus=applicable_skus,
                    applicable_stores=all_store_ids,
                    source_connector=CONNECTOR_NAME,
                ))
        return promos

    # ------------------------------------------------------------------
    # Temporal simulation
    # ------------------------------------------------------------------

    def _run_simulation(self) -> None:
        """
        Day-by-day simulation.  Internally tracks latent demand and stock levels
        to generate realistic orders and POs.  Nothing derived (demand curves,
        reorder thresholds) is persisted — only raw operational records.
        """
        n_prod = len(self._products)
        n_store = len(self._stores)

        # Base demand per product (units/day across all stores, before any multipliers)
        base_demands: dict[str, float] = {}
        for p in self._products:
            tier = p.attributes.get("tier", "standard")
            if tier == "bestseller":
                base_demands[p.id] = self._rng.uniform(1.2, 3.5)
            elif tier == "standard":
                base_demands[p.id] = self._rng.uniform(0.25, 1.2)
            else:
                base_demands[p.id] = self._rng.uniform(0.02, 0.25)

        # Store demand multipliers
        store_dm: dict[str, float] = {}
        for i, s in enumerate(self._stores):
            store_dm[s.id] = _STORE_DEFS[i]["dm"]

        # Initial stock: ~90 days of average demand per series
        stock: dict[tuple[str, str], float] = {}
        for p in self._products:
            for s in self._stores:
                avg_daily = base_demands[p.id] * store_dm[s.id]
                stock[(p.id, s.id)] = max(10.0, round(avg_daily * 90))

        # In-transit PO tracking: on_order[key] = total units en route
        on_order: dict[tuple[str, str], float] = {}
        # Arrivals scheduled: date → list of (product_id, store_id, quantity)
        arrivals: dict[date, list[tuple[str, str, float]]] = {}

        # Build date → active promotions lookup
        promo_by_date: dict[date, list[RawPromotion]] = {}
        for promo in self._promotions:
            if promo.start_date and promo.end_date:
                d = promo.start_date
                while d <= promo.end_date:
                    if self._start_date <= d <= self._end_date:
                        promo_by_date.setdefault(d, []).append(promo)
                    d += timedelta(days=1)

        # Product launch date lookup
        launch_dates: dict[str, date] = {}
        for p in self._products:
            ld_str = p.attributes.get("launch_date", "")
            launch_dates[p.id] = date.fromisoformat(ld_str) if ld_str else self._start_date

        order_counter = 0
        po_counter    = 0
        wholesale_id  = "store_005"
        outlet_id     = "store_004"

        current_date = self._start_date
        while current_date <= self._end_date:

            # 1. Process arriving POs
            for prod_id, store_id, qty in arrivals.pop(current_date, []):
                key = (prod_id, store_id)
                stock[key] = stock.get(key, 0.0) + qty
                on_order[key] = max(0.0, on_order.get(key, 0.0) - qty)

            active_promos = promo_by_date.get(current_date, [])
            dow_f   = _DOW_FACTOR[current_date.weekday()]
            month_f = _MONTH_FACTOR[current_date.month]

            for p in self._products:
                if launch_dates[p.id] > current_date:
                    continue

                base = base_demands[p.id]

                for s in self._stores:
                    key = (p.id, s.id)
                    sm  = store_dm[s.id]

                    # Promotion uplift
                    promo_uplift  = 1.0
                    active_promo_id: Optional[str] = None
                    active_disc_pct = 0.0
                    for promo in active_promos:
                        if promo.applicable_skus and p.sku not in promo.applicable_skus:
                            continue
                        if promo.applicable_stores and s.id not in promo.applicable_stores:
                            continue
                        # uplift: 10% off → ~1.45×, 35% off → ~2.57×
                        uplift = 1.0 + promo.discount_pct * 4.5
                        if uplift > promo_uplift:
                            promo_uplift    = uplift
                            active_promo_id = promo.id
                            active_disc_pct = promo.discount_pct

                    # Latent demand (internal — not persisted)
                    lam = base * sm * dow_f * month_f * promo_uplift
                    demand_units = self._poisson(lam)

                    # Cap by available stock
                    available    = max(0.0, stock.get(key, 0.0))
                    actual_units = min(float(demand_units), available)
                    actual_units = math.floor(actual_units)

                    if actual_units > 0:
                        stock[key] = stock.get(key, 0.0) - actual_units
                        order_counter = self._emit_order_lines(
                            p, s, current_date, actual_units,
                            active_promo_id, active_disc_pct,
                            order_counter, wholesale_id, outlet_id,
                        )

                    # Daily inventory snapshot
                    snap_id = f"inv_{p.id}_{s.id}_{current_date.isoformat()}"
                    self._inventory.append(RawInventorySnapshot(
                        id=snap_id,
                        store_id=s.id,
                        product_id=p.id,
                        snapshot_date=current_date,
                        quantity_on_hand=max(0.0, stock.get(key, 0.0)),
                        quantity_on_order=on_order.get(key, 0.0),
                        quantity_reserved=0.0,
                        source_connector=CONNECTOR_NAME,
                    ))

                    # Reorder decision (internal logic — drives PO generation only)
                    avg_daily      = base * sm * _MONTH_FACTOR[current_date.month]
                    reorder_thresh = avg_daily * 30.0
                    current_stock  = stock.get(key, 0.0)
                    already_on_ord = on_order.get(key, 0.0) > 0

                    if current_stock < reorder_thresh and not already_on_ord:
                        supplier = next(
                            (sup for sup in self._suppliers if sup.id == p.supplier_id), None
                        )
                        if supplier:
                            lt_min  = supplier.lead_time_days_min or 7
                            lt_max  = supplier.lead_time_days_max or 21
                            nominal = self._rng.randint(lt_min, lt_max)
                            delay   = self._rng.randint(2, 7) if self._rng.random() > supplier.reliability_score else 0
                            actual_lt    = nominal + delay
                            arrival_date = current_date + timedelta(days=actual_lt)
                            order_qty    = max(20.0, round(avg_daily * 60))

                            po_counter += 1
                            status = "received" if arrival_date <= self._end_date else "confirmed"

                            self._purchase_orders.append(RawPurchaseOrder(
                                id=f"po_{po_counter:07d}",
                                external_po_id=f"EXT-PO-{po_counter:07d}",
                                supplier_id=supplier.id,
                                product_id=p.id,
                                store_id=s.id,
                                ordered_at=datetime.combine(current_date, dt_time(9, 0)),
                                expected_delivery_date=arrival_date,
                                quantity_ordered=order_qty,
                                unit_cost=p.unit_cost,
                                status=status,
                                source_connector=CONNECTOR_NAME,
                            ))

                            on_order[key] = on_order.get(key, 0.0) + order_qty
                            if arrival_date <= self._end_date:
                                arrivals.setdefault(arrival_date, []).append(
                                    (p.id, s.id, order_qty)
                                )

            current_date += timedelta(days=1)

    def _emit_order_lines(
        self,
        p: RawProduct,
        s: RawStore,
        current_date: date,
        actual_units: float,
        active_promo_id: Optional[str],
        active_disc_pct: float,
        order_counter: int,
        wholesale_id: str,
        outlet_id: str,
    ) -> int:
        """Emit raw order line(s) for actual_units sold. Returns updated counter."""
        unit_price = p.unit_price or 10.0

        if s.id == wholesale_id:
            # Wholesale: single bulk order line
            order_counter += 1
            disc = round(unit_price * self._rng.uniform(0.28, 0.42), 2)
            self._orders.append(RawOrderLine(
                id=f"ord_{order_counter:09d}",
                external_order_id=f"WHL-{order_counter:09d}",
                store_id=s.id,
                product_id=p.id,
                ordered_at=datetime.combine(current_date, dt_time(self._rng.randint(8, 17), 0)),
                order_date=current_date,
                quantity=float(actual_units),
                unit_price=unit_price,
                discount_amount=disc * actual_units,
                currency=self.config.currency,
                status="fulfilled",
                promotion_id=active_promo_id,
                source_connector=CONNECTOR_NAME,
            ))
        else:
            # Retail/online/outlet: split into individual-ish transactions
            remaining = int(actual_units)
            while remaining > 0:
                qty = min(remaining, self._rng.randint(1, 2))
                remaining -= qty
                order_counter += 1

                h = self._rng.randint(8, 22)
                m = self._rng.randint(0, 59)
                if s.id == outlet_id:
                    disc = round(unit_price * self._rng.uniform(0.15, 0.35), 2)
                elif active_promo_id:
                    disc = round(unit_price * active_disc_pct, 2)
                else:
                    disc = 0.0

                self._orders.append(RawOrderLine(
                    id=f"ord_{order_counter:09d}",
                    external_order_id=f"ORD-{order_counter:09d}",
                    store_id=s.id,
                    product_id=p.id,
                    ordered_at=datetime.combine(current_date, dt_time(h, m)),
                    order_date=current_date,
                    quantity=float(qty),
                    unit_price=unit_price,
                    discount_amount=disc * qty,
                    currency=self.config.currency,
                    status=self._rand_order_status(),
                    promotion_id=active_promo_id,
                    source_connector=CONNECTOR_NAME,
                ))

        return order_counter

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _poisson(self, lam: float) -> int:
        """Knuth Poisson sampler (pure Python). Falls back to Gaussian approx for lam>30."""
        if lam <= 0:
            return 0
        if lam > 30:
            val = round(lam + math.sqrt(lam) * self._rng.gauss(0, 1))
            return max(0, int(val))
        L = math.exp(-min(lam, 700))
        k, p = 0, 1.0
        while p > L:
            k += 1
            p *= self._rng.random()
        return k - 1

    def _rand_order_status(self) -> str:
        r = self._rng.random()
        if r < 0.88:
            return "fulfilled"
        if r < 0.95:
            return "pending"
        if r < 0.98:
            return "cancelled"
        return "returned"

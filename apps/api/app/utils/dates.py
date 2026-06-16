from datetime import date, timedelta


def date_range(start: date, end: date) -> list[date]:
    """Inclusive list of dates from start to end."""
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def last_n_days(n: int, reference: date | None = None) -> tuple[date, date]:
    """Return (start, end) covering the last n days ending on reference (default today)."""
    end = reference or date.today()
    start = end - timedelta(days=n - 1)
    return start, end

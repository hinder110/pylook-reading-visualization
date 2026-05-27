"""Generate reading visualization dashboard from Legado backup data."""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def load_read_records():
    path = os.path.join(BACKUP_DIR, "readRecord.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_bookshelf():
    path = os.path.join(BACKUP_DIR, "bookshelf.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ms_to_datetime(ms_timestamp):
    """Convert millisecond epoch to datetime."""
    return datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc)


def normalize_book_name(name):
    """Strip file extension and parenthetical suffixes."""
    name = name.strip()
    if name.endswith(".epub"):
        name = name[:-5]
    # Remove trailing parenthetical groups like "(作者名) (Z-Library)"
    while "(" in name and name.rstrip().endswith(")"):
        last_open = name.rfind("(")
        name = name[:last_open].rstrip()
    return name


def clean_records(records):
    """Merge duplicate books by name, filter zero readTime, add hours."""
    merged = {}
    for r in records:
        if r["readTime"] <= 0:
            continue
        name = normalize_book_name(r["bookName"])
        if name in merged:
            merged[name]["readTime"] += r["readTime"]
            merged[name]["lastRead"] = max(merged[name]["lastRead"], r["lastRead"])
        else:
            merged[name] = {
                "bookName": name,
                "readTime": r["readTime"],
                "lastRead": r["lastRead"],
            }
    result = list(merged.values())
    for r in result:
        r["hours"] = r["readTime"] / 3600.0
    return result


def prepare_rank_data(records, top_n=20):
    """Sort by hours descending, return top N + other aggregation."""
    sorted_records = sorted(records, key=lambda r: r["hours"], reverse=True)
    top = sorted_records[:top_n]
    rest = sorted_records[top_n:]
    other_hours = sum(r["hours"] for r in rest)
    return top, other_hours, len(rest)


def prepare_monthly_data(records):
    """Aggregate reading hours by month based on lastRead date."""
    monthly = defaultdict(lambda: {"hours": 0.0, "books": []})
    for r in records:
        dt = ms_to_datetime(r["lastRead"])
        month_key = dt.strftime("%Y-%m")
        monthly[month_key]["hours"] += r["hours"]
        monthly[month_key]["books"].append(r["bookName"])
    result = [
        {"month": k, "hours": v["hours"], "books": v["books"]}
        for k, v in sorted(monthly.items())
    ]
    return result


def prepare_distribution_data(records):
    """Extract hours list for histogram and box plot."""
    return [r["hours"] for r in records]

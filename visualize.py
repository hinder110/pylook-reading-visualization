"""Generate reading visualization dashboard from Legado backup data."""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict

import plotly.graph_objects as go
import plotly.subplots

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


def create_distribution_chart(hours_list):
    """Side-by-side histogram and box plot of reading hours distribution."""
    fig = plotly.subplots.make_subplots(
        rows=1, cols=2,
        subplot_titles=("阅读时长分布 (直方图)", "阅读时长分布 (箱线图)"),
        column_widths=[0.6, 0.4],
    )

    fig.add_trace(go.Histogram(
        x=hours_list,
        nbinsx=30,
        name="书籍数量",
        hovertemplate="%{x:.0f} 小时: %{y} 本<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Box(
        x=hours_list,
        name="阅读时长",
        hovertemplate="%{x:.1f} 小时<extra></extra>",
    ), row=1, col=2)

    fig.update_layout(
        title="阅读时长分布",
        showlegend=False,
        height=400,
        font=dict(family="Sarasa Gothic SC, Source Han Sans CN, sans-serif"),
    )
    fig.update_xaxes(title_text="阅读时长 (小时)", row=1, col=1)
    fig.update_xaxes(title_text="", row=1, col=2)
    fig.update_yaxes(title_text="书籍数量", row=1, col=1)
    return fig

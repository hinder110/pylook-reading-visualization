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


def create_rank_chart(top20, other_hours, other_count):
    """Horizontal bar chart: Top 20 books by reading hours + '其他'."""
    names = [r["bookName"] for r in top20]
    hours = [r["hours"] for r in top20]

    if other_count > 0:
        names.append(f"其他 ({other_count}本)")
        hours.append(other_hours)

    # Reverse so highest is at top
    names = list(reversed(names))
    hours = list(reversed(hours))

    text = [f"{h:.1f} 小时" for h in hours]

    fig = go.Figure()
    colors = ["#636EFA"] * len(top20)
    if other_count > 0:
        colors.append("#CCCCCC")
    colors = list(reversed(colors))

    fig.add_trace(go.Bar(
        x=hours,
        y=names,
        orientation="h",
        text=text,
        textposition="outside",
        marker_color=colors,
        hovertemplate="%{y}<br>%{x:.1f} 小时<extra></extra>",
    ))

    fig.update_layout(
        title="阅读时长排名 (Top 20)",
        xaxis_title="小时",
        yaxis_title="",
        margin=dict(l=10, r=30, t=40, b=10),
        height=600,
        font=dict(family="Sarasa Gothic SC, Source Han Sans CN, sans-serif"),
    )
    return fig


def create_timeline_chart(monthly_data):
    """Bar chart: monthly reading hours, colored by year."""
    months = [d["month"] for d in monthly_data]
    hours = [d["hours"] for d in monthly_data]
    books = [", ".join(d["books"][:5]) + ("..." if len(d["books"]) > 5 else "")
             for d in monthly_data]

    # Color by year
    years = [m[:4] for m in months]
    unique_years = sorted(set(years))
    color_map = {
        y: f"hsl({i * 360 // len(unique_years)}, 60%, 50%)"
        for i, y in enumerate(unique_years)
    }
    colors = [color_map[y] for y in years]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=hours,
        marker_color=colors,
        hovertemplate="%{x}<br>%{y:.1f} 小时<br>%{customdata}<extra></extra>",
        customdata=books,
    ))

    fig.update_layout(
        title="月度阅读时间线",
        xaxis_title="月份",
        yaxis_title="阅读时长 (小时)",
        xaxis=dict(tickangle=-45),
        margin=dict(l=10, r=10, t=40, b=60),
        height=450,
        font=dict(family="Sarasa Gothic SC, Source Han Sans CN, sans-serif"),
    )
    return fig

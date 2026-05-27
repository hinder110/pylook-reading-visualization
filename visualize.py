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


def prepare_shelf_data(shelf_books, records):
    """Prepare table data from bookshelf merged with read records."""
    record_map = {normalize_book_name(r["bookName"]): r for r in records}
    rows = []
    for b in shelf_books:
        name = b.get("name", "未知")
        author = b.get("author", "未知")
        if not author or author.strip() == "":
            author = "未知"
        dur_title = b.get("durChapterTitle", "")
        dur_time = b.get("durChapterTime", 0)
        total_chapters = b.get("totalChapterNum", 0)
        dur_idx = b.get("durChapterIndex", 0)

        last_read_dt = ms_to_datetime(dur_time) if dur_time else None
        last_read_str = last_read_dt.strftime("%Y-%m-%d") if last_read_dt else "未知"

        if total_chapters > 0 and total_chapters < 10000:
            progress = (dur_idx / total_chapters) * 100
        else:
            progress = None

        norm_name = normalize_book_name(name)
        total_hours = None
        if norm_name in record_map:
            total_hours = record_map[norm_name].get("hours")

        rows.append({
            "bookName": name[:30],
            "author": author[:20],
            "chapter": dur_title[:25] if dur_title else "",
            "lastRead": last_read_str,
            "progress": progress,
            "totalHours": total_hours,
            "lastReadTs": dur_time,
        })

    rows.sort(key=lambda r: r["lastReadTs"], reverse=True)
    return rows


def create_shelf_chart(shelf_rows):
    """Table of shelf books."""
    header = ["书名", "作者", "当前章节", "最后阅读", "进度", "总阅读时长"]
    cells = [[], [], [], [], [], []]
    for r in shelf_rows:
        cells[0].append(r["bookName"])
        cells[1].append(r["author"])
        cells[2].append(r["chapter"])
        cells[3].append(r["lastRead"])
        if r["progress"] is not None:
            cells[4].append(f"{r['progress']:.1f}%")
        else:
            cells[4].append("-")
        if r["totalHours"] is not None:
            cells[5].append(f"{r['totalHours']:.1f}h")
        else:
            cells[5].append("-")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=header,
            fill_color="paleturquoise",
            align="left",
            font=dict(size=12),
        ),
        cells=dict(
            values=cells,
            fill_color="lavender",
            align="left",
            font=dict(size=11),
        ),
    )])

    fig.update_layout(
        title="书架状态",
        height=300 + 30 * len(shelf_rows),
        font=dict(family="Sarasa Gothic SC, Source Han Sans CN, sans-serif"),
    )
    return fig


def create_calendar_heatmap(records):
    """Calendar heatmap of reading activity by date."""
    date_counts = defaultdict(int)
    for r in records:
        d = ms_to_datetime(r["lastRead"]).date()
        date_counts[d.isoformat()] += 1

    if not date_counts:
        return go.Figure()

    dates = sorted(date_counts.keys())
    counts = [date_counts[d] for d in dates]

    fig = go.Figure(data=[go.Heatmap(
        z=counts,
        x=dates,
        y=["阅读活动"],
        colorscale="YlOrRd",
        showscale=True,
        hovertemplate="%{x}<br>%{z} 本书<extra></extra>",
    )])

    fig.update_layout(
        title="每日阅读活动热力图",
        height=120,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="Sarasa Gothic SC, Source Han Sans CN, sans-serif"),
        xaxis=dict(tickformat="%Y-%m", dtick="M3"),
    )
    return fig


def build_html(figs):
    """Assemble all figures into a single self-contained HTML page."""
    titles = [
        "阅读时长排名",
        "月度阅读时间线",
        "阅读时长分布",
        "书架状态",
        "每日阅读活动",
    ]

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>阅读可视化报告</title>",
        '<script src="https://cdn.plot.ly/plotly-3.1.0.min.js"></script>',
        "<style>",
        "body { font-family: 'Sarasa Gothic SC', 'Source Han Sans CN', sans-serif; "
        "max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }",
        "h1 { text-align: center; color: #333; }",
        ".chart { background: white; border-radius: 8px; padding: 16px; "
        "margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>📚 阅读可视化报告</h1>",
    ]

    for i, fig in enumerate(figs):
        div_id = f"chart_{i}"
        html_parts.append(f'<div class="chart" id="{div_id}">')
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)


def main():
    """Generate the reading visualization report."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    records = load_read_records()
    shelf = load_bookshelf()

    cleaned = clean_records(records)

    top20, other_hours, other_count = prepare_rank_data(cleaned)
    monthly = prepare_monthly_data(cleaned)
    hours_list = prepare_distribution_data(cleaned)
    shelf_rows = prepare_shelf_data(shelf, cleaned)

    figs = [
        create_rank_chart(top20, other_hours, other_count),
        create_timeline_chart(monthly),
        create_distribution_chart(hours_list),
        create_shelf_chart(shelf_rows),
        create_calendar_heatmap(cleaned),
    ]

    html = build_html(figs)
    output_path = os.path.join(OUTPUT_DIR, "reading_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report generated: {output_path}")
    print(f"Books: {len(cleaned)}, Shelf: {len(shelf)}")
    total_hours = sum(r["hours"] for r in cleaned)
    print(f"Total reading time: {total_hours:.0f} hours ({total_hours/24:.1f} days)")


if __name__ == "__main__":
    main()

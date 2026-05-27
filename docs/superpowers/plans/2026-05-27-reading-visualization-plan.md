# Reading Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate interactive HTML dashboard with 4 Plotly charts from Legado reading backup data.

**Architecture:** Single `visualize.py` script. Data loading/cleaning functions are pure and testable. Chart functions take prepared data, return Plotly figures. Output is one self-contained HTML file with embedded Plotly.js via CDN. PNG export via Plotly's built-in toolbar button (no kaleido needed).

**Tech Stack:** Python 3.14, Plotly 6.7, matplotlib (for test validation only), Sarasa Gothic font for Chinese

---

## File Structure

| File | Purpose |
|------|---------|
| `visualize.py` | All data + chart logic, single entry point |
| `tests/test_data.py` | Tests for data loading/cleaning/preparation |
| `backup/*.json` | Input data (read-only) |
| `output/reading_report.html` | Generated HTML dashboard |

---

### Task 1: Create project structure and test skeleton

**Files:**
- Create: `tests/test_data.py`

- [ ] **Step 1: Create test file with data loading tests**

```python
"""Tests for reading data processing functions."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualize import load_read_records, load_bookshelf


def test_load_read_records():
    records = load_read_records()
    assert isinstance(records, list)
    assert len(records) > 0
    assert all("bookName" in r for r in records)
    assert all("readTime" in r for r in records)
    assert all("lastRead" in r for r in records)


def test_load_bookshelf():
    shelf = load_bookshelf()
    assert isinstance(shelf, list)
    assert len(shelf) > 0
    assert all("name" in b for b in shelf)
    assert all("author" in b for b in shelf)
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/test_data.py -v`
Expected: FAIL with ModuleNotFoundError (no visualize.py yet)

- [ ] **Step 3: Create visualize.py with minimal load functions**

```python
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
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `python3 -m pytest tests/test_data.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_data.py visualize.py
git commit -m "feat: add data loading functions and tests"
```

---

### Task 2: Data cleaning — deduplicate and normalize

**Files:**
- Modify: `visualize.py` (add clean functions)
- Modify: `tests/test_data.py` (add tests)

- [ ] **Step 1: Write tests for data cleaning**

```python
from visualize import clean_records, ms_to_datetime, normalize_book_name


def test_ms_to_datetime():
    dt = ms_to_datetime(1726324367668)
    assert dt.year == 2024
    assert dt.month == 9
    assert dt.day == 14


def test_normalize_book_name_removes_author_suffix():
    name = "带上她的眼睛 (刘慈欣) (Z-Library)"
    result = normalize_book_name(name)
    assert "刘慈欣" not in result
    assert "Z-Library" not in result
    assert "带上她的眼睛" in result


def test_normalize_book_name_removes_epub_extension():
    name = "精要主义 (摒弃琐碎而无足轻重的生活，过真正重要而有意义的人生！).epub"
    result = normalize_book_name(name)
    assert ".epub" not in result


def test_clean_records_merges_duplicates():
    records = [
        {"bookName": "带上她的眼睛", "readTime": 100, "lastRead": 1000},
        {"bookName": "带上她的眼睛", "readTime": 200, "lastRead": 2000},
        {"bookName": "三体", "readTime": 500, "lastRead": 3000},
    ]
    result = clean_records(records)
    names = [r["bookName"] for r in result]
    assert len(result) == 2
    assert "带上她的眼睛" in names
    assert "三体" in names
    # Merged: readTime summed, lastRead is latest
    merged = [r for r in result if r["bookName"] == "带上她的眼睛"][0]
    assert merged["readTime"] == 300
    assert merged["lastRead"] == 2000


def test_clean_records_filters_zero_readtime():
    records = [
        {"bookName": "空", "readTime": 0, "lastRead": 1000},
        {"bookName": "有", "readTime": 100, "lastRead": 2000},
    ]
    result = clean_records(records)
    assert len(result) == 1
    assert result[0]["bookName"] == "有"


def test_clean_records_adds_hours():
    records = [
        {"bookName": "测试", "readTime": 7200, "lastRead": 1000},
    ]
    result = clean_records(records)
    assert result[0]["hours"] == 2.0
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/test_data.py::test_ms_to_datetime tests/test_data.py::test_normalize_book_name_removes_author_suffix tests/test_data.py::test_normalize_book_name_removes_epub_extension tests/test_data.py::test_clean_records_merges_duplicates tests/test_data.py::test_clean_records_filters_zero_readtime tests/test_data.py::test_clean_records_adds_hours -v`
Expected: FAIL (functions not defined)

- [ ] **Step 3: Implement cleaning functions**

In `visualize.py`, add after the load functions:

```python
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
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `python3 -m pytest tests/test_data.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add visualize.py tests/test_data.py
git commit -m "feat: add data cleaning with dedup, normalization, and unit conversion"
```

---

### Task 3: Data preparation — rank, monthly, distribution

**Files:**
- Modify: `visualize.py` (add prepare functions)
- Modify: `tests/test_data.py` (add tests)

- [ ] **Step 1: Write tests for data preparation**

```python
from visualize import prepare_rank_data, prepare_monthly_data, prepare_distribution_data


def test_prepare_rank_data_top20():
    records = []
    for i in range(30):
        records.append({
            "bookName": f"Book{i}",
            "hours": float(30 - i),
            "readTime": (30 - i) * 3600,
        })
    top20, other_hours, other_count = prepare_rank_data(records, top_n=20)
    assert len(top20) == 20
    assert other_count == 10
    assert other_hours > 0


def test_prepare_rank_data_small_list():
    records = [{"bookName": "A", "hours": 1.0, "readTime": 3600}]
    top20, other_hours, other_count = prepare_rank_data(records, top_n=20)
    assert len(top20) == 1
    assert other_count == 0
    assert other_hours == 0


def test_prepare_monthly_data():
    from datetime import datetime, timezone
    records = [
        {"bookName": "A", "hours": 10.0, "lastRead": int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000)},
        {"bookName": "B", "hours": 5.0, "lastRead": int(datetime(2024, 1, 20, tzinfo=timezone.utc).timestamp() * 1000)},
        {"bookName": "C", "hours": 3.0, "lastRead": int(datetime(2024, 3, 10, tzinfo=timezone.utc).timestamp() * 1000)},
    ]
    result = prepare_monthly_data(records)
    months = [r["month"] for r in result]
    assert "2024-01" in months
    assert "2024-03" in months
    jan = [r for r in result if r["month"] == "2024-01"][0]
    assert jan["hours"] == 15.0
    assert "A" in jan["books"]
    assert "B" in jan["books"]


def test_prepare_distribution_data():
    records = [
        {"hours": 1.0}, {"hours": 2.0}, {"hours": 3.0},
        {"hours": 10.0}, {"hours": 100.0},
    ]
    hours_list = prepare_distribution_data(records)
    assert hours_list == [1.0, 2.0, 3.0, 10.0, 100.0]
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/test_data.py::test_prepare_rank_data_top20 tests/test_data.py::test_prepare_rank_data_small_list tests/test_data.py::test_prepare_monthly_data tests/test_data.py::test_prepare_distribution_data -v`
Expected: FAIL

- [ ] **Step 3: Implement preparation functions**

In `visualize.py`, add:

```python
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
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `python3 -m pytest tests/test_data.py -v`
Expected: 12 PASS

- [ ] **Step 5: Commit**

```bash
git add visualize.py tests/test_data.py
git commit -m "feat: add data preparation for rank, monthly, and distribution charts"
```

---

### Task 4: Chart 1 — Reading time rank (Top 20 bar chart)

**Files:**
- Modify: `visualize.py` (add `create_rank_chart`)

- [ ] **Step 1: Write test for rank chart structure**

```python
from visualize import create_rank_chart


def test_create_rank_chart():
    top20 = [
        {"bookName": "三体", "hours": 100.0, "readTime": 360000},
        {"bookName": "龙族", "hours": 50.0, "readTime": 180000},
    ]
    other_hours = 30.0
    other_count = 5
    fig = create_rank_chart(top20, other_hours, other_count)
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 3  # 2 books + "其他"
    assert "三体" in fig.data[0].y
    assert "其他" in fig.data[0].y[-1]
```

- [ ] **Step 2: Run test to confirm failure**

Run: `python3 -m pytest tests/test_data.py::test_create_rank_chart -v`
Expected: FAIL

- [ ] **Step 3: Implement rank chart**

In `visualize.py`, add:

```python
import plotly.graph_objects as go
import plotly.subplots


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
```

- [ ] **Step 4: Run test to confirm pass**

Run: `python3 -m pytest tests/test_data.py::test_create_rank_chart -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add visualize.py tests/test_data.py
git commit -m "feat: add reading time rank chart (top 20)"
```

---

### Task 5: Chart 2 — Monthly reading timeline

**Files:**
- Modify: `visualize.py` (add `create_timeline_chart`)

- [ ] **Step 1: Implement timeline chart (no separate test — visual output, test through structure check)**

In `visualize.py`, add:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add visualize.py
git commit -m "feat: add monthly reading timeline chart"
```

---

### Task 6: Chart 3 — Reading time distribution

**Files:**
- Modify: `visualize.py` (add `create_distribution_chart`)

- [ ] **Step 1: Implement distribution chart**

In `visualize.py`, add:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add visualize.py
git commit -m "feat: add reading time distribution charts"
```

---

### Task 7: Chart 4 — Shelf status table + calendar heatmap

**Files:**
- Modify: `visualize.py` (add `prepare_shelf_data`, `create_shelf_chart`)

- [ ] **Step 1: Implement shelf preparation and chart**

In `visualize.py`, add:

```python
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
    """Table of shelf books + calendar heatmap of last-read dates."""
    from datetime import date

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
    from datetime import date as dt_date, timedelta

    date_counts = defaultdict(int)
    for r in records:
        d = ms_to_datetime(r["lastRead"]).date()
        date_counts[d.isoformat()] += 1

    if not date_counts:
        return go.Figure()

    dates = sorted(date_counts.keys())
    dates_iso = dates
    counts = [date_counts[d] for d in dates]

    fig = go.Figure(data=[go.Heatmap(
        z=counts,
        x=dates_iso,
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
```

- [ ] **Step 2: Commit**

```bash
git add visualize.py
git commit -m "feat: add shelf status table and calendar heatmap"
```

---

### Task 8: HTML assembly and main entry point

**Files:**
- Modify: `visualize.py` (add `build_html`, `main`)

- [ ] **Step 1: Implement HTML assembly and main**

In `visualize.py`, add:

```python
def build_html(figs):
    """Assemble all figures into a single self-contained HTML page."""
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
        "<h1>阅读可视化报告</h1>",
    ]

    titles = [
        "阅读时长排名",
        "月度阅读时间线",
        "阅读时长分布",
        "书架状态",
        "每日阅读活动",
    ]
    for fig, title in zip(figs, titles):
        div_id = f"chart_{titles.index(title)}"
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
```

Note: update the `build_html` signature and `titles` list — use `enumerate` for `div_id` assignment.

- [ ] **Step 2: Run the script**

Run: `python3 visualize.py`
Expected: "Report generated: .../output/reading_report.html"

- [ ] **Step 3: Verify HTML file exists**

Run: `ls -la output/reading_report.html`
Expected: File exists, > 0 bytes

- [ ] **Step 4: Commit**

```bash
git add visualize.py
git commit -m "feat: add HTML assembly and main entry point"
```

---

### Task 9: Integration verification

**Files:**
- None (verify only)

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/test_data.py -v`
Expected: All tests pass

- [ ] **Step 2: Run the script from scratch**

```bash
rm -rf output/
python3 visualize.py
```

Expected: Output directory created, HTML file generated, summary stats printed.

- [ ] **Step 3: Check for data issues in console output**

Run: `python3 visualize.py 2>&1`
Expected: No errors or warnings. Summary shows reasonable totals.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final integration verification"
```

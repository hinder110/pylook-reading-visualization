# Reading Visualization Design

## Scope

Generate interactive HTML dashboard + static PNG charts from Legado reading backup data. Single Python script, no server, no framework.

## Data Sources

| File | Content | Key Fields |
|------|---------|------------|
| `backup/readRecord.json` | 62 reading records | `bookName`, `readTime` (seconds), `lastRead` (ms epoch) |
| `backup/bookshelf.json` | 37 shelf books | `name`, `author`, `durChapterTitle`, `durChapterTime`, `totalChapterNum`, `durChapterIndex` |

### Data Cleaning

- `readTime` seconds → hours for display
- `lastRead` / `durChapterTime` ms epoch → datetime
- Duplicate book names merged (e.g. "带上她的眼睛" appears twice, "七周七并发模型" appears 3 times)

## Output

- `output/reading_report.html` — single self-contained HTML with Plotly charts
- `output/png/` — 4 static screenshots

## Charts

### 1. Reading Time Rank (Top 20)

Horizontal bar chart. Book names left, hours right. Sorted descending. Bottom bar: "其他 (N本)" in gray, aggregating remaining books. Hover shows exact minutes.

### 2. Monthly Reading Timeline

Bar chart. X-axis: months (YYYY-MM). Y-axis: total reading hours. Color by year. Hover lists books read that month.

### 3. Reading Time Distribution

Side-by-side histogram and box plot. Histogram bins by hour ranges. Box plot shows median, quartiles, outliers. Unit: hours.

### 4. Shelf Status

Table: book name, author, current chapter, last read date, progress %. Sorted by last read descending. Side panel: calendar heatmap of reading frequency.

## Tech Stack

- Python 3, Plotly (interactive HTML), Kaleido (PNG export)
- Font: Sarasa Gothic / Source Han Sans for Chinese rendering

## Edge Cases

- Zero readTime: skip from charts, note in log
- Missing author: show "未知"
- Duplicate names: merge readTime, keep latest lastRead
- Very long book names: truncate to 20 chars in bar chart labels

"""Tests for reading data processing functions."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualize import load_read_records, load_bookshelf, clean_records, ms_to_datetime, normalize_book_name, prepare_rank_data, prepare_monthly_data, prepare_distribution_data


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

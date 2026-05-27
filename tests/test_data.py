"""Tests for reading data processing functions."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualize import load_read_records, load_bookshelf, clean_records, ms_to_datetime, normalize_book_name


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

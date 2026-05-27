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

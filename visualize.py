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

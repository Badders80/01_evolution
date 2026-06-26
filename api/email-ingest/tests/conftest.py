import os
import sys

INGEST_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if INGEST_DIR not in sys.path:
    sys.path.insert(0, INGEST_DIR)
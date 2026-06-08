import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_firestore():
    """Prevent Firestore from connecting to GCP during tests."""
    mock_db = MagicMock()
    # Patch at module level to prevent import errors when google.cloud.firestore
    # is not available (e.g., running without venv activated)
    try:
        import google.cloud.firestore
    except ImportError:
        google = MagicMock()
        google.cloud = MagicMock()
        google.cloud.firestore = MagicMock()
        import sys
        sys.modules['google'] = google
        sys.modules['google.cloud'] = google.cloud
        sys.modules['google.cloud.firestore'] = google.cloud.firestore
    with patch("google.cloud.firestore.Client", return_value=mock_db):
        yield mock_db

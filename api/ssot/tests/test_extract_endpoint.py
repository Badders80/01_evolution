"""Unit tests for the /extract endpoint proxy."""

import pytest
import json
from unittest.mock import patch, MagicMock

from routes.extract import parse_loveracing_url, scrape_loveracing_page, handle


class TestParseLoveracingUrl:
    """Test URL validation."""

    def test_valid_url(self):
        lid, slug = parse_loveracing_url(
            "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"
        )
        assert lid == 427416
        assert slug == "Prudentia-NZ-2021"

    def test_invalid_url(self):
        lid, slug = parse_loveracing_url("https://example.com")
        assert lid is None
        assert slug is None

    def test_caselower(self):
        lid, slug = parse_loveracing_url(
            "https://loveracing.nz/Breeding/1/Test-Horse.aspx"
        )
        assert lid == 1
        assert slug == "Test-Horse"


class TestScrapeProxy:
    """Test proxy to racing-data Cloud Function."""

    @patch("routes.extract.RACING_DATA_URL", "http://racing-data")
    @patch("routes.extract.requests.post")
    def test_scrape_success(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "loveracing_id": 427416,
                "name": "Prudentia (NZ) 2021",
                "name_slug": "Prudentia-NZ-2021",
                "microchip": "985125000126462",
                "life_number": "NZ00427416",
            },
            raise_for_status=lambda: None,
        )

        result = scrape_loveracing_page(
            "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
            427416,
            "Prudentia-NZ-2021",
        )

        mock_post.assert_called_once_with(
            "http://racing-data/loveracing/427416",
            json={
                "url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
                "name_slug": "Prudentia-NZ-2021",
            },
            timeout=120,
        )
        assert result["loveracing_id"] == 427416
        assert result["microchip"] == "985125000126462"

    @patch("routes.extract.RACING_DATA_URL", "")
    def test_scrape_no_config(self):
        with pytest.raises(ValueError, match="RACING_DATA_URL not configured"):
            scrape_loveracing_page("https://example.com", 1, "test")


class TestHandle:
    """Test route handler with mocked proxy."""

    def _make_request(self, method="POST", json_body=None):
        req = MagicMock()
        req.method = method
        req.get_json.return_value = json_body
        return req

    @patch("routes.extract.scrape_loveracing_page")
    def test_handle_success(self, mock_scrape):
        from flask import Flask
        app = Flask(__name__)
        mock_scrape.return_value = {
            "loveracing_id": 427416,
            "name": "Prudentia (NZ) 2021",
        }
        req = self._make_request(
            json_body={"url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"}
        )
        with app.app_context():
            response, status = handle(req)
        assert status == 200
        data = json.loads(response.data)
        assert data["loveracing_id"] == 427416

    def test_handle_method_not_allowed(self):
        from flask import Flask
        app = Flask(__name__)
        req = self._make_request(method="GET")
        with app.app_context():
            response, status = handle(req)
        assert status == 405

    def test_handle_missing_url(self):
        from flask import Flask
        app = Flask(__name__)
        req = self._make_request(json_body={})
        with app.app_context():
            response, status = handle(req)
        assert status == 400
        data = json.loads(response.data)
        assert "url" in data["error"].lower()

    def test_handle_invalid_url(self):
        from flask import Flask
        app = Flask(__name__)
        req = self._make_request(json_body={"url": "https://example.com"})
        with app.app_context():
            response, status = handle(req)
        assert status == 400
        data = json.loads(response.data)
        assert "invalid" in data["error"].lower()

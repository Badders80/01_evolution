"""Tests for the Document Record API (Sprint S5)."""

import pytest
from datetime import date, datetime
from pydantic import ValidationError
from models import (
    DocumentRecordCreate,
    DocumentRecord,
    DocumentRecordUpdate,
    ReviewSection,
    build_default_sections,
    DOC_TYPE_SECTIONS,
    DocReviewStatus,
    SectionReviewStatus,
)


# ─── Model Validation ─────────────────────────────────────────────────────────

class TestReviewSection:
    def test_valid_section_defaults(self):
        rs = ReviewSection(section_name="horse_details")
        assert rs.status == "pending"
        assert rs.reviewer_notes is None

    def test_valid_section_with_notes(self):
        rs = ReviewSection(section_name="pricing", status="approved", reviewer_notes="Numbers verified")
        assert rs.status == "approved"
        assert rs.reviewer_notes == "Numbers verified"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            ReviewSection(section_name="foo", status="invalid_status")


class TestDocumentRecordCreate:
    def test_valid_create(self):
        dr = DocumentRecordCreate(
            document_id="DOC-LSE-001-PDS",
            lease_id="LSE-001",
            horse_id="985125000126462",
            document_type="pds",
            document_version=1,
            document_date=date(2026, 6, 9),
            file_path="gs://evolution-horse-docs/hlt-001/pds.docx",
        )
        assert dr.doc_review_status == "draft"
        assert dr.is_current is True
        assert dr.document_version == 1

    def test_invalid_document_type(self):
        with pytest.raises(ValidationError):
            DocumentRecordCreate(
                document_id="DOC-LSE-001-FOO",
                lease_id="LSE-001",
                horse_id="985125000126462",
                document_type="invalid",  # not in Literal
                document_version=1,
                document_date=date(2026, 6, 9),
                file_path="gs://bucket/file.docx",
            )

    def test_invalid_version_zero(self):
        with pytest.raises(ValidationError):
            DocumentRecordCreate(
                document_id="DOC-LSE-001-PDS",
                lease_id="LSE-001",
                horse_id="985125000126462",
                document_type="pds",
                document_version=0,
                document_date=date(2026, 6, 9),
                file_path="gs://bucket/file.docx",
            )

    def test_sections_default_empty(self):
        dr = DocumentRecordCreate(
            document_id="DOC-LSE-001-PDS",
            lease_id="LSE-001",
            horse_id="985125000126462",
            document_type="pds",
            document_version=1,
            document_date=date(2026, 6, 9),
            file_path="gs://bucket/file.docx",
        )
        assert dr.sections == []

    def test_sections_with_review_items(self):
        sections = [
            ReviewSection(section_name="overview", status="approved"),
            ReviewSection(section_name="risks", status="needs_revision", reviewer_notes="Add NZTR clause"),
        ]
        dr = DocumentRecordCreate(
            document_id="DOC-LSE-001-PDS",
            lease_id="LSE-001",
            horse_id="985125000126462",
            document_type="pds",
            document_version=1,
            document_date=date(2026, 6, 9),
            file_path="gs://bucket/file.docx",
            sections=sections,
        )
        assert len(dr.sections) == 2
        assert dr.sections[1].reviewer_notes == "Add NZTR clause"


class TestDocumentRecordFull:
    def test_server_fields_required(self):
        dr = DocumentRecord(
            id="doc-firestore-123",
            created_at=datetime(2026, 6, 9, 10, 0, 0),
            updated_at=datetime(2026, 6, 9, 10, 0, 0),
            document_id="DOC-LSE-001-PDS",
            lease_id="LSE-001",
            horse_id="985125000126462",
            document_type="pds",
            document_version=1,
            document_date=date(2026, 6, 9),
            file_path="gs://bucket/file.docx",
        )
        assert dr.id == "doc-firestore-123"


class TestDocumentRecordUpdate:
    def test_partial_update(self):
        upd = DocumentRecordUpdate(
            doc_review_status="review",
            notes="Pending legal review",
        )
        assert upd.doc_review_status == "review"
        assert upd.notes == "Pending legal review"
        assert upd.document_version is None

    def test_invalid_status_update(self):
        with pytest.raises(ValidationError):
            DocumentRecordUpdate(doc_review_status="not_a_status")


# ─── Section Builder ──────────────────────────────────────────────────────────

class TestBuildDefaultSections:
    def test_term_sheet_sections(self):
        secs = build_default_sections("term-sheet")
        names = [s.section_name for s in secs]
        assert names == ["horse_details", "lease_terms", "pricing", "parties"]
        assert all(s.status == "pending" for s in secs)

    def test_pds_sections(self):
        secs = build_default_sections("pds")
        names = [s.section_name for s in secs]
        assert names == ["overview", "horse_details", "lease_terms", "risks", "fees", "contact"]

    def test_sa_sections(self):
        secs = build_default_sections("sa")
        names = [s.section_name for s in secs]
        assert names == ["parties", "lease_conditions", "payment_terms", "termination", "governing_law"]

    def test_unknown_doc_type_returns_empty(self):
        secs = build_default_sections("unknown")
        assert secs == []

    def test_doc_type_sections_map_complete(self):
        assert set(DOC_TYPE_SECTIONS.keys()) == {"term-sheet", "pds", "sa"}


# ─── Status Transition Logic ────────────────────────────────────────────────

class TestDocReviewStatusTransitions:
    """Test the auto-derive logic that docs.py review() uses."""

    def _derive_status(self, sections: list[dict]) -> str:
        """Mirror the logic from docs.py review()."""
        all_approved = all(s.get("status") == "approved" for s in sections)
        any_rejected = any(s.get("status") == "rejected" for s in sections)
        any_needs_revision = any(s.get("status") == "needs_revision" for s in sections)

        if all_approved and len(sections) > 0:
            return "approved"
        if any_rejected:
            return "rejected"
        if any_needs_revision:
            return "review"
        return "draft"

    def test_all_approved(self):
        sections = [
            {"section_name": "a", "status": "approved"},
            {"section_name": "b", "status": "approved"},
        ]
        assert self._derive_status(sections) == "approved"

    def test_any_rejected_overrides_all_approved(self):
        sections = [
            {"section_name": "a", "status": "approved"},
            {"section_name": "b", "status": "rejected"},
        ]
        assert self._derive_status(sections) == "rejected"

    def test_needs_revision(self):
        sections = [
            {"section_name": "a", "status": "approved"},
            {"section_name": "b", "status": "needs_revision"},
        ]
        assert self._derive_status(sections) == "review"

    def test_empty_sections_stays_draft(self):
        assert self._derive_status([]) == "draft"

    def test_all_pending_stays_draft(self):
        sections = [
            {"section_name": "a", "status": "pending"},
            {"section_name": "b", "status": "pending"},
        ]
        assert self._derive_status(sections) == "draft"


# ─── Route-Level Mock Tests ───────────────────────────────────────────────────

class TestDocsRoutes:
    def test_list_by_lease_missing_param(self):
        """Mock test: list_by_lease without lease_id returns 400."""
        from unittest.mock import MagicMock, patch
        from flask import Flask
        import ssot.routes.docs as docs_module

        app = Flask(__name__)
        with patch.object(docs_module, "_get_db") as mock_get_db:
            mock_request = MagicMock()
            mock_request.method = "GET"
            mock_request.args = {}
            mock_request.get_json.return_value = {}

            with app.app_context():
                resp, status = docs_module.list_by_lease(mock_request)
            assert status == 400

    def test_get_document_not_found(self):
        from unittest.mock import MagicMock, patch
        from flask import Flask
        import ssot.routes.docs as docs_module

        app = Flask(__name__)
        with patch.object(docs_module, "_get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            mock_get_db.return_value = mock_db

            mock_request = MagicMock()
            mock_request.method = "GET"

            with app.app_context():
                resp, status = docs_module.get_document(mock_request, "DOC-NONEXISTENT")
            assert status == 404

    def test_review_document_not_found(self):
        from unittest.mock import MagicMock, patch
        from flask import Flask
        import ssot.routes.docs as docs_module

        app = Flask(__name__)
        with patch.object(docs_module, "_get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            mock_get_db.return_value = mock_db

            mock_request = MagicMock()
            mock_request.method = "POST"
            mock_request.get_json.return_value = {"sections": {}}

            with app.app_context():
                resp, status = docs_module.review(mock_request, "DOC-NONEXISTENT")
            assert status == 404

"""Tests for the Assets API."""

import pytest
from models import AssetCreate


class TestAssetCreate:
    """Test AssetCreate Pydantic model validation."""

    def test_valid_horse_image(self):
        asset = AssetCreate(
            entity_type="horse",
            entity_id="985125000126462",
            asset_type="image",
            gcs_url="gs://evolution-horse-images/horse/985125000126462/abc123.jpg",
            public_url="https://storage.googleapis.com/evolution-horse-images/horse/985125000126462/abc123.jpg",
            file_name="horse_photo.jpg",
            mime_type="image/jpeg",
            file_size_bytes=1024000,
            is_primary=True,
        )
        assert asset.entity_type == "horse"
        assert asset.entity_id == "985125000126462"
        assert asset.is_primary is True

    def test_default_entity_type_is_horse(self):
        asset = AssetCreate(
            entity_id="985125000126462",
            asset_type="image",
            gcs_url="gs://bucket/file.jpg",
            public_url="https://bucket/file.jpg",
            file_name="file.jpg",
            mime_type="image/jpeg",
            file_size_bytes=1000,
        )
        assert asset.entity_type == "horse"

    def test_asset_type_must_be_valid(self):
        with pytest.raises(ValidationError):
            AssetCreate(
                entity_type="horse",
                entity_id="985125000126462",
                asset_type="invalid",
                gcs_url="gs://bucket/file.jpg",
                public_url="https://bucket/file.jpg",
                file_name="file.jpg",
                mime_type="image/jpeg",
                file_size_bytes=1000,
            )
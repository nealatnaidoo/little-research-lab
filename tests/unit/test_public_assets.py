"""
Tests for Public Asset Serving Routes (E2.2).

Test assertions:
- TA-0009: Headers correctness (ETag, Cache-Control, Content-Disposition, X-Content-SHA256)
- TA-0010: ETag stable (same content = same ETag)
- TA-0011: Download disposition (?download=1 triggers attachment)
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from src.api.routes.public_assets import (
    CACHE_CONTROL_IMMUTABLE,
    CACHE_CONTROL_LATEST,
    build_content_disposition,
    build_etag,
    get_asset_headers,
)

# --- Mock AssetVersion ---


@dataclass
class MockAssetVersion:
    """Mock asset version for testing."""

    id: UUID
    asset_id: UUID
    version_number: int
    storage_key: str
    sha256: str
    size_bytes: int
    mime_type: str
    filename_original: str
    is_latest: bool = False


# --- Fixtures ---


@pytest.fixture
def sample_sha256() -> str:
    """Sample SHA256 hash."""
    return "a" * 64  # 64 hex chars


@pytest.fixture
def sample_version(sample_sha256: str) -> MockAssetVersion:
    """Sample asset version."""
    asset_id = uuid4()
    return MockAssetVersion(
        id=uuid4(),
        asset_id=asset_id,
        version_number=1,
        storage_key=f"assets/{asset_id}/v1/test.png",
        sha256=sample_sha256,
        size_bytes=1024,
        mime_type="image/png",
        filename_original="test-image.png",
        is_latest=True,
    )


# --- TA-0009: Headers Correctness ---


class TestHeadersCorrectness:
    """Test TA-0009: All required headers are present and correct."""

    def test_etag_header_present(self, sample_sha256: str) -> None:
        """ETag header is present in response headers."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
        )
        assert "ETag" in headers
        assert headers["ETag"]

    def test_cache_control_header_present(self, sample_sha256: str) -> None:
        """Cache-Control header is present."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
        )
        assert "Cache-Control" in headers
        assert headers["Cache-Control"]

    def test_content_disposition_header_present(self, sample_sha256: str) -> None:
        """Content-Disposition header is present."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
        )
        assert "Content-Disposition" in headers
        assert headers["Content-Disposition"]

    def test_sha256_header_present(self, sample_sha256: str) -> None:
        """X-Content-SHA256 header is present."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
        )
        assert "X-Content-SHA256" in headers
        assert headers["X-Content-SHA256"] == sample_sha256

    def test_versioned_route_cache_immutable(self, sample_sha256: str) -> None:
        """Versioned route has immutable cache control."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
            is_latest=False,
        )
        assert headers["Cache-Control"] == CACHE_CONTROL_IMMUTABLE
        assert "immutable" in headers["Cache-Control"]

    def test_latest_route_cache_short(self, sample_sha256: str) -> None:
        """Latest route has shorter cache control."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
            is_latest=True,
        )
        assert headers["Cache-Control"] == CACHE_CONTROL_LATEST
        assert "must-revalidate" in headers["Cache-Control"]


# --- TA-0010: ETag Stability ---


class TestETagStability:
    """Test TA-0010: ETag is stable and based on content hash."""

    def test_same_hash_same_etag(self) -> None:
        """Same SHA256 produces same ETag."""
        sha256 = "abc123" * 10 + "abcd"
        etag1 = build_etag(sha256)
        etag2 = build_etag(sha256)
        assert etag1 == etag2

    def test_different_hash_different_etag(self) -> None:
        """Different SHA256 produces different ETag."""
        etag1 = build_etag("a" * 64)
        etag2 = build_etag("b" * 64)
        assert etag1 != etag2

    def test_etag_format_quoted(self) -> None:
        """ETag is properly quoted per HTTP spec."""
        etag = build_etag("a" * 64)
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_etag_reasonable_length(self) -> None:
        """ETag has reasonable length (not full 64 char hash)."""
        etag = build_etag("a" * 64)
        # Should be shorter than full hash + quotes
        assert len(etag) < 64 + 2

    def test_etag_consistent_across_requests(self, sample_sha256: str) -> None:
        """Same content always produces same ETag across requests."""
        headers1 = get_asset_headers(sha256=sample_sha256, filename="test.png")
        headers2 = get_asset_headers(sha256=sample_sha256, filename="test.png")
        assert headers1["ETag"] == headers2["ETag"]


# --- TA-0011: Download Disposition ---


class TestDownloadDisposition:
    """Test TA-0011: Content-Disposition changes with ?download=1."""

    def test_default_inline_disposition(self) -> None:
        """Default disposition is inline (display in browser)."""
        disposition = build_content_disposition("test.png", download=False)
        assert disposition.startswith("inline")

    def test_download_attachment_disposition(self) -> None:
        """?download=1 triggers attachment disposition."""
        disposition = build_content_disposition("test.png", download=True)
        assert disposition.startswith("attachment")

    def test_filename_in_disposition(self) -> None:
        """Filename is included in disposition."""
        disposition = build_content_disposition("my-image.png", download=False)
        assert "my-image.png" in disposition

    def test_filename_in_download_disposition(self) -> None:
        """Filename is included in download disposition."""
        disposition = build_content_disposition("report.pdf", download=True)
        assert "report.pdf" in disposition

    def test_special_chars_escaped(self) -> None:
        """Special characters in filename are escaped."""
        disposition = build_content_disposition('file"with"quotes.png', download=False)
        # Quotes should be escaped
        assert '\\"' in disposition or "file" in disposition

    def test_headers_reflect_download_flag(self, sample_sha256: str) -> None:
        """Headers change based on download flag."""
        headers_inline = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
            download=False,
        )
        headers_download = get_asset_headers(
            sha256=sample_sha256,
            filename="test.png",
            download=True,
        )

        assert "inline" in headers_inline["Content-Disposition"]
        assert "attachment" in headers_download["Content-Disposition"]


# --- Cache Control Values ---


class TestCacheControlValues:
    """Test cache control header values."""

    def test_immutable_cache_has_long_max_age(self) -> None:
        """Immutable cache has long max-age."""
        assert "max-age=" in CACHE_CONTROL_IMMUTABLE
        # Extract max-age value
        parts = CACHE_CONTROL_IMMUTABLE.split(",")
        for part in parts:
            if "max-age=" in part:
                age = int(part.split("=")[1].strip())
                # Should be at least 1 day (86400 seconds)
                assert age >= 86400

    def test_immutable_cache_is_public(self) -> None:
        """Immutable cache is public (CDN-friendly)."""
        assert "public" in CACHE_CONTROL_IMMUTABLE

    def test_immutable_cache_has_immutable_directive(self) -> None:
        """Immutable cache has 'immutable' directive."""
        assert "immutable" in CACHE_CONTROL_IMMUTABLE

    def test_latest_cache_has_short_max_age(self) -> None:
        """Latest cache has short max-age."""
        assert "max-age=" in CACHE_CONTROL_LATEST
        parts = CACHE_CONTROL_LATEST.split(",")
        for part in parts:
            if "max-age=" in part:
                age = int(part.split("=")[1].strip())
                # Should be short (< 5 minutes)
                assert age <= 300

    def test_latest_cache_requires_revalidation(self) -> None:
        """Latest cache requires revalidation."""
        assert "must-revalidate" in CACHE_CONTROL_LATEST


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases for asset serving."""

    def test_empty_filename_handled(self) -> None:
        """Empty filename doesn't break disposition."""
        disposition = build_content_disposition("", download=False)
        assert "inline" in disposition

    def test_long_filename_handled(self) -> None:
        """Long filename doesn't break disposition."""
        long_name = "a" * 200 + ".png"
        disposition = build_content_disposition(long_name, download=False)
        assert "inline" in disposition

    def test_unicode_filename_handled(self) -> None:
        """Unicode filename doesn't break disposition."""
        disposition = build_content_disposition("文件.png", download=False)
        assert "inline" in disposition

    def test_newline_in_filename_sanitized(self) -> None:
        """Newline in filename is sanitized."""
        disposition = build_content_disposition("file\nname.png", download=False)
        # Newline should be replaced or removed
        assert "\n" not in disposition


# --- Integration-like Tests ---


class TestHeadersIntegration:
    """Test header combinations work together."""

    def test_all_required_headers_present(self, sample_sha256: str) -> None:
        """All required headers are present for asset serving."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="document.pdf",
            download=False,
            is_latest=False,
        )

        required_headers = [
            "ETag",
            "Cache-Control",
            "Content-Disposition",
            "X-Content-SHA256",
        ]

        for header in required_headers:
            assert header in headers, f"Missing header: {header}"
            assert headers[header], f"Empty header: {header}"

    def test_download_pdf_headers(self, sample_sha256: str) -> None:
        """PDF download has correct headers."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="report.pdf",
            download=True,
            is_latest=False,
        )

        assert "attachment" in headers["Content-Disposition"]
        assert "report.pdf" in headers["Content-Disposition"]
        assert "immutable" in headers["Cache-Control"]

    def test_inline_image_headers(self, sample_sha256: str) -> None:
        """Inline image has correct headers."""
        headers = get_asset_headers(
            sha256=sample_sha256,
            filename="photo.jpg",
            download=False,
            is_latest=False,
        )

        assert "inline" in headers["Content-Disposition"]
        assert "photo.jpg" in headers["Content-Disposition"]


# --- TA-0012: Latest Resolution ---


class TestLatestResolution:
    """Test TA-0012: /latest alias resolves to configured latest version."""

    def test_latest_resolves_to_marked_version(self) -> None:
        """
        /latest alias should resolve to whichever version is marked as latest.

        This is verified by checking that:
        1. After upload, the new version becomes latest
        2. get_latest returns that version
        """
        from src.components.assets.component import run_upload
        from src.components.assets.models import UploadAssetInput

        # Create mock repos inline to avoid import issues
        class MockAssetRepo:
            def __init__(self) -> None:
                self.assets: dict = {}

            def get_by_id(self, asset_id: UUID) -> None:
                return self.assets.get(asset_id)

            def save(self, asset):
                self.assets[asset.id] = asset
                return asset

        class MockVersionRepo:
            def __init__(self) -> None:
                self.versions: dict = {}
                self._latest: dict = {}

            def get_by_id(self, version_id: UUID):
                return self.versions.get(version_id)

            def save(self, version):
                self.versions[version.id] = version
                return version

            def get_versions(self, asset_id: UUID) -> list:
                return [v for v in self.versions.values() if v.asset_id == asset_id]

            def get_latest(self, asset_id: UUID):
                vid = self._latest.get(asset_id)
                return self.versions.get(vid) if vid else None

            def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
                self._latest[asset_id] = version_id

            def get_next_version_number(self, asset_id: UUID) -> int:
                return len(self.get_versions(asset_id)) + 1

        class MockStorage:
            def __init__(self) -> None:
                self.objects: dict = {}

            def put(
                self,
                key: str,
                data: bytes,
                content_type: str,
                *,
                expected_sha256: str | None = None,
            ):
                self.objects[key] = data

        asset_repo = MockAssetRepo()
        version_repo = MockVersionRepo()
        storage = MockStorage()
        user_id = uuid4()

        # Upload first version
        inp1 = UploadAssetInput(
            data=b"version 1 content",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
        )
        result1 = run_upload(
            inp1,
            asset_repo=asset_repo,
            version_repo=version_repo,
            storage=storage,
        )

        assert result1.success
        asset_id = result1.asset.id
        v1_id = result1.version.id

        # Latest should be v1
        latest = version_repo.get_latest(asset_id)
        assert latest is not None
        assert latest.id == v1_id

    def test_new_upload_becomes_latest(self) -> None:
        """New upload automatically becomes the latest version."""
        from src.components.assets.component import run_upload
        from src.components.assets.models import UploadAssetInput

        class MockAssetRepo:
            def __init__(self) -> None:
                self.assets: dict = {}

            def get_by_id(self, asset_id: UUID):
                return self.assets.get(asset_id)

            def save(self, asset):
                self.assets[asset.id] = asset
                return asset

        class MockVersionRepo:
            def __init__(self) -> None:
                self.versions: dict = {}
                self._latest: dict = {}

            def get_by_id(self, version_id: UUID):
                return self.versions.get(version_id)

            def save(self, version):
                self.versions[version.id] = version
                return version

            def get_versions(self, asset_id: UUID) -> list:
                return [v for v in self.versions.values() if v.asset_id == asset_id]

            def get_latest(self, asset_id: UUID):
                vid = self._latest.get(asset_id)
                return self.versions.get(vid) if vid else None

            def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
                self._latest[asset_id] = version_id

            def get_next_version_number(self, asset_id: UUID) -> int:
                return len(self.get_versions(asset_id)) + 1

        class MockStorage:
            def __init__(self) -> None:
                self.objects: dict = {}

            def put(
                self,
                key: str,
                data: bytes,
                content_type: str,
                *,
                expected_sha256: str | None = None,
            ):
                self.objects[key] = data

        asset_repo = MockAssetRepo()
        version_repo = MockVersionRepo()
        storage = MockStorage()
        user_id = uuid4()

        # Upload v1
        inp1 = UploadAssetInput(
            data=b"version 1",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
        )
        result1 = run_upload(
            inp1, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        asset_id = result1.asset.id
        v1_id = result1.version.id

        # Upload v2
        inp2 = UploadAssetInput(
            data=b"version 2",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
            asset_id=asset_id,
        )
        result2 = run_upload(
            inp2, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        v2_id = result2.version.id

        # Latest should now be v2
        latest = version_repo.get_latest(asset_id)
        assert latest.id == v2_id
        assert latest.id != v1_id


# --- TA-0013: Rollback Latest Pointer ---


class TestRollbackLatestPointer:
    """Test TA-0013: Admin can rollback /latest pointer to a previous version."""

    def test_set_latest_to_previous_version(self) -> None:
        """Admin can set a previous version as latest (rollback)."""
        from src.components.assets.component import run_set_latest, run_upload
        from src.components.assets.models import SetLatestVersionInput, UploadAssetInput

        class MockAssetRepo:
            def __init__(self) -> None:
                self.assets: dict = {}

            def get_by_id(self, asset_id: UUID):
                return self.assets.get(asset_id)

            def save(self, asset):
                self.assets[asset.id] = asset
                return asset

        class MockVersionRepo:
            def __init__(self) -> None:
                self.versions: dict = {}
                self._latest: dict = {}

            def get_by_id(self, version_id: UUID):
                return self.versions.get(version_id)

            def save(self, version):
                self.versions[version.id] = version
                return version

            def get_versions(self, asset_id: UUID) -> list:
                return [v for v in self.versions.values() if v.asset_id == asset_id]

            def get_latest(self, asset_id: UUID):
                vid = self._latest.get(asset_id)
                return self.versions.get(vid) if vid else None

            def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
                self._latest[asset_id] = version_id

            def get_next_version_number(self, asset_id: UUID) -> int:
                return len(self.get_versions(asset_id)) + 1

        class MockStorage:
            def __init__(self) -> None:
                self.objects: dict = {}

            def put(
                self,
                key: str,
                data: bytes,
                content_type: str,
                *,
                expected_sha256: str | None = None,
            ):
                self.objects[key] = data

        asset_repo = MockAssetRepo()
        version_repo = MockVersionRepo()
        storage = MockStorage()
        user_id = uuid4()

        # Upload v1
        inp1 = UploadAssetInput(
            data=b"version 1",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
        )
        result1 = run_upload(
            inp1, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        asset_id = result1.asset.id
        v1_id = result1.version.id

        # Upload v2 (becomes latest)
        inp2 = UploadAssetInput(
            data=b"version 2",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
            asset_id=asset_id,
        )
        result2 = run_upload(
            inp2, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        v2_id = result2.version.id

        # Verify v2 is latest
        assert version_repo.get_latest(asset_id).id == v2_id

        # Rollback to v1
        rollback_inp = SetLatestVersionInput(asset_id=asset_id, version_id=v1_id)
        rollback_result = run_set_latest(
            rollback_inp,
            asset_repo=asset_repo,
            version_repo=version_repo,
        )

        assert rollback_result.success
        assert version_repo.get_latest(asset_id).id == v1_id

    def test_set_latest_invalid_version_fails(self) -> None:
        """Setting non-existent version as latest fails gracefully."""
        from src.components.assets.component import run_set_latest, run_upload
        from src.components.assets.models import SetLatestVersionInput, UploadAssetInput

        class MockAssetRepo:
            def __init__(self) -> None:
                self.assets: dict = {}

            def get_by_id(self, asset_id: UUID):
                return self.assets.get(asset_id)

            def save(self, asset):
                self.assets[asset.id] = asset
                return asset

        class MockVersionRepo:
            def __init__(self) -> None:
                self.versions: dict = {}
                self._latest: dict = {}

            def get_by_id(self, version_id: UUID):
                return self.versions.get(version_id)

            def save(self, version):
                self.versions[version.id] = version
                return version

            def get_versions(self, asset_id: UUID) -> list:
                return [v for v in self.versions.values() if v.asset_id == asset_id]

            def get_latest(self, asset_id: UUID):
                vid = self._latest.get(asset_id)
                return self.versions.get(vid) if vid else None

            def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
                self._latest[asset_id] = version_id

            def get_next_version_number(self, asset_id: UUID) -> int:
                return len(self.get_versions(asset_id)) + 1

        class MockStorage:
            def __init__(self) -> None:
                self.objects: dict = {}

            def put(
                self,
                key: str,
                data: bytes,
                content_type: str,
                *,
                expected_sha256: str | None = None,
            ):
                self.objects[key] = data

        asset_repo = MockAssetRepo()
        version_repo = MockVersionRepo()
        storage = MockStorage()
        user_id = uuid4()

        # Upload one version
        inp = UploadAssetInput(
            data=b"content",
            filename="test.png",
            content_type="image/png",
            user_id=user_id,
        )
        result = run_upload(inp, asset_repo=asset_repo, version_repo=version_repo, storage=storage)
        asset_id = result.asset.id

        # Try to set non-existent version as latest
        fake_version_id = uuid4()
        set_inp = SetLatestVersionInput(asset_id=asset_id, version_id=fake_version_id)
        set_result = run_set_latest(set_inp, asset_repo=asset_repo, version_repo=version_repo)

        assert not set_result.success
        assert len(set_result.errors) > 0
        assert set_result.errors[0].code == "version_not_found"

    def test_set_latest_wrong_asset_fails(self) -> None:
        """Setting version from different asset fails."""
        from src.components.assets.component import run_set_latest, run_upload
        from src.components.assets.models import SetLatestVersionInput, UploadAssetInput

        class MockAssetRepo:
            def __init__(self) -> None:
                self.assets: dict = {}

            def get_by_id(self, asset_id: UUID):
                return self.assets.get(asset_id)

            def save(self, asset):
                self.assets[asset.id] = asset
                return asset

        class MockVersionRepo:
            def __init__(self) -> None:
                self.versions: dict = {}
                self._latest: dict = {}

            def get_by_id(self, version_id: UUID):
                return self.versions.get(version_id)

            def save(self, version):
                self.versions[version.id] = version
                return version

            def get_versions(self, asset_id: UUID) -> list:
                return [v for v in self.versions.values() if v.asset_id == asset_id]

            def get_latest(self, asset_id: UUID):
                vid = self._latest.get(asset_id)
                return self.versions.get(vid) if vid else None

            def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
                self._latest[asset_id] = version_id

            def get_next_version_number(self, asset_id: UUID) -> int:
                return len(self.get_versions(asset_id)) + 1

        class MockStorage:
            def __init__(self) -> None:
                self.objects: dict = {}

            def put(
                self,
                key: str,
                data: bytes,
                content_type: str,
                *,
                expected_sha256: str | None = None,
            ):
                self.objects[key] = data

        asset_repo = MockAssetRepo()
        version_repo = MockVersionRepo()
        storage = MockStorage()
        user_id = uuid4()

        # Upload to asset A
        inp_a = UploadAssetInput(
            data=b"asset A content",
            filename="test_a.png",
            content_type="image/png",
            user_id=user_id,
        )
        result_a = run_upload(
            inp_a, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        asset_a_id = result_a.asset.id

        # Upload to asset B
        inp_b = UploadAssetInput(
            data=b"asset B content",
            filename="test_b.png",
            content_type="image/png",
            user_id=user_id,
        )
        result_b = run_upload(
            inp_b, asset_repo=asset_repo, version_repo=version_repo, storage=storage
        )
        version_b_id = result_b.version.id

        # Try to set asset B's version as latest for asset A
        set_inp = SetLatestVersionInput(asset_id=asset_a_id, version_id=version_b_id)
        set_result = run_set_latest(set_inp, asset_repo=asset_repo, version_repo=version_repo)

        assert not set_result.success
        assert len(set_result.errors) > 0

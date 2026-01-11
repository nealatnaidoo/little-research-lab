from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.domain.entities import User
from src.rules.models import UploadsRules
from src.services.asset import AssetService


@pytest.fixture
def mock_repo():
    return Mock()

@pytest.fixture
def mock_filestore():
    return Mock()

@pytest.fixture
def mock_policy():
    return Mock()

@pytest.fixture
def rules():
    return UploadsRules(
        max_upload_bytes=1000,
        allowlist_mime_types=["image/png"],
        allowlist_extensions=[".png"],
        quarantine={"enabled": False},
        # Assuming other fields have defaults or I need to provide them if no defaults.
        # Checking UploadsRules model: dict[str, bool] for quarantine.
    )

@pytest.fixture
def service(mock_repo, mock_filestore, mock_policy, rules):
    return AssetService(mock_repo, mock_filestore, mock_policy, rules)

def test_upload_asset_success(service, mock_policy, mock_filestore, mock_repo):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["editor"]
    )
    mock_policy.check_permission.return_value = True
    mock_filestore.save.return_value = "storage/path"

    data = b"fake data"
    asset = service.upload_asset(user, "test.png", "image/png", data)

    assert asset.filename_original == "test.png"
    assert asset.mime_type == "image/png"
    assert asset.storage_path == "storage/path"
    
    mock_policy.check_permission.assert_called_with(user, user.roles, "asset:create")
    mock_filestore.save.assert_called()
    mock_repo.save.assert_called_with(asset)

def test_upload_asset_denied(service, mock_policy):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["viewer"]
    )
    mock_policy.check_permission.return_value = False
    
    with pytest.raises(PermissionError):
        service.upload_asset(user, "test.png", "image/png", b"data")

def test_upload_asset_size_limit(service, mock_policy):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["editor"]
    )
    mock_policy.check_permission.return_value = True
    
    # Limit is 1000 bytes
    data = b"a" * 1001
    
    with pytest.raises(ValueError, match="File size exceeds limit"):
        service.upload_asset(user, "test.png", "image/png", data)

def test_upload_asset_invalid_ext(service, mock_policy):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["editor"]
    )
    mock_policy.check_permission.return_value = True
    
    # Mismatch ext/mime but ext check fails first
    with pytest.raises(ValueError, match="Extension '.jpg' is not allowed"):
        service.upload_asset(user, "test.jpg", "image/png", b"data")

def test_upload_asset_invalid_mime(service, mock_policy):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["editor"]
    )
    mock_policy.check_permission.return_value = True
    
    with pytest.raises(ValueError, match="MIME type 'image/jpeg' is not allowed"):
        service.upload_asset(user, "test.png", "image/jpeg", b"data")

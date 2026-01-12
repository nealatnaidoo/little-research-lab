from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.components.assets.component import run, run_set_latest
from src.components.assets.models import SetLatestOutput, SetLatestVersionInput
from src.components.assets.ports import AssetRepoPort, VersionRepoPort
from src.core.entities import Asset, AssetVersion


@pytest.fixture
def mock_asset_repo():
    return Mock(spec=AssetRepoPort)


@pytest.fixture
def mock_version_repo():
    return Mock(spec=VersionRepoPort)


def test_run_set_latest_success(mock_asset_repo, mock_version_repo):
    asset_id = uuid4()
    version_id = uuid4()

    # Setup mocks
    mock_version = Mock(spec=AssetVersion)
    mock_version.id = version_id
    mock_version.asset_id = asset_id
    mock_version.storage_key = "key1"
    mock_version.sha256 = "hash1"
    mock_version.size_bytes = 123

    mock_version_repo.get_by_id.return_value = mock_version

    mock_asset = Mock(spec=Asset)
    mock_asset.id = asset_id
    mock_asset_repo.get_by_id.return_value = mock_asset

    # Input
    inp = SetLatestVersionInput(asset_id=asset_id, version_id=version_id)

    # Execute
    output = run_set_latest(inp, asset_repo=mock_asset_repo, version_repo=mock_version_repo)

    # Verify
    assert output.success is True
    assert len(output.errors) == 0

    # Check interactions
    mock_version_repo.set_latest.assert_called_once_with(asset_id, version_id)
    mock_asset_repo.save.assert_called_once()
    assert mock_asset.storage_path == "key1"


def test_run_set_latest_version_not_found(mock_asset_repo, mock_version_repo):
    asset_id = uuid4()
    version_id = uuid4()

    # Mock return None
    mock_version_repo.get_by_id.return_value = None

    inp = SetLatestVersionInput(asset_id=asset_id, version_id=version_id)
    output = run_set_latest(inp, asset_repo=mock_asset_repo, version_repo=mock_version_repo)

    assert output.success is False
    assert len(output.errors) == 1
    assert output.errors[0].code == "version_not_found"


def test_run_dispatcher_set_latest(mock_asset_repo, mock_version_repo):
    asset_id = uuid4()
    version_id = uuid4()

    # Setup mocks
    mock_version = Mock(spec=AssetVersion)
    mock_version.id = version_id
    mock_version.asset_id = asset_id
    mock_version.storage_key = "key2"
    mock_version.sha256 = "hash2"
    mock_version.size_bytes = 456
    mock_version_repo.get_by_id.return_value = mock_version

    mock_asset = Mock(spec=Asset)
    mock_asset_repo.get_by_id.return_value = mock_asset

    inp = SetLatestVersionInput(asset_id=asset_id, version_id=version_id)

    # Call via main run() dispatcher
    output = run(inp, asset_repo=mock_asset_repo, version_repo=mock_version_repo)

    assert isinstance(output, SetLatestOutput)
    assert output.success is True

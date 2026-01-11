from typing import Protocol

from src.ports.auth import AuthPort
from src.ports.clock import ClockPort
from src.ports.filestore import FileStorePort
from src.ports.renderer import RendererPort
from src.ports.repo import AssetRepoPort, ContentRepoPort, LinkRepoPort


def test_ports_are_protocols():
    """Verify all defined ports inherit from Protocol."""
    assert issubclass(ContentRepoPort, Protocol)
    assert issubclass(LinkRepoPort, Protocol)
    assert issubclass(AssetRepoPort, Protocol)
    assert issubclass(FileStorePort, Protocol)
    assert issubclass(ClockPort, Protocol)
    assert issubclass(AuthPort, Protocol)
    assert issubclass(RendererPort, Protocol)

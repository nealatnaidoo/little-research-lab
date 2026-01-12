import pytest

from src.adapters.fs.filestore import FileSystemStore


@pytest.fixture
def store(tmp_path):
    return FileSystemStore(str(tmp_path / "store"))


def test_save_and_read(store):
    store.save("test.txt", b"hello world")
    data = store.get("test.txt")
    assert data == b"hello world"


def test_overwrite(store):
    store.save("overwrite.txt", b"v1")
    store.save("overwrite.txt", b"v2")
    assert store.get("overwrite.txt") == b"v2"


def test_delete(store):
    store.save("zombie.txt", b"brains")
    store.delete("zombie.txt")
    with pytest.raises(FileNotFoundError):
        store.get("zombie.txt")


def test_path_traversal(store):
    with pytest.raises(ValueError):
        store.save("../hack.txt", b"bad")

    with pytest.raises(ValueError):
        store.get("/etc/passwd")


def test_nested_folders(store):
    store.save("foo/bar/baz.txt", b"nested")
    assert store.get("foo/bar/baz.txt") == b"nested"

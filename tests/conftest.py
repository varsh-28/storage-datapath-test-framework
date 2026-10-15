import pytest

from src.filesystem_client import FileSystemClient


@pytest.fixture
def fs_client(tmp_path):
    return FileSystemClient(tmp_path / "storage")

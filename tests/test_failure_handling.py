
import pytest


def test_read_missing_file(fs_client):
    with pytest.raises(FileNotFoundError):
        fs_client.read_file("missing.bin")


def test_checksum_missing_file(fs_client):
    with pytest.raises(FileNotFoundError):
        fs_client.checksum("missing.bin")


def test_write_rejects_non_bytes_data(fs_client):
    with pytest.raises(TypeError):
        fs_client.write_file("invalid.bin", "this is text")


def test_rejects_parent_directory_traversal(fs_client):
    with pytest.raises(ValueError):
        fs_client.write_file("../outside.bin", b"unsafe")

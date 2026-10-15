
import pytest


def test_rejects_empty_filename(fs_client):
    with pytest.raises(ValueError):
        fs_client.write_file("", b"test")


def test_rejects_absolute_path(fs_client):
    with pytest.raises(ValueError):
        fs_client.write_file("C:\\temp\\outside.bin", b"test")


def test_delete_file_removes_file(fs_client):
    fs_client.write_file("delete-me.bin", b"temporary data")

    fs_client.delete_file("delete-me.bin")

    assert not fs_client.file_exists("delete-me.bin")


def test_delete_missing_file_raises_error(fs_client):
    with pytest.raises(FileNotFoundError):
        fs_client.delete_file("does-not-exist.bin")

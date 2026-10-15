import os
import pytest


def test_file_exists_and_size(fs_client):
    payload = b"x" * 12345
    fs_client.write_file("metadata.bin", payload)

    assert fs_client.file_exists("metadata.bin")
    assert fs_client.file_size("metadata.bin") == 12345


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics required")
def test_file_permissions_can_be_changed(tmp_path, fs_client):
    path = fs_client.write_file("permissions.bin", b"permission test")
    path.chmod(0o600)

    assert path.stat().st_mode & 0o777 == 0o600

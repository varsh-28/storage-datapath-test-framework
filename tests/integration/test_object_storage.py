import hashlib

import pytest


pytestmark = pytest.mark.integration


def test_object_upload_download_and_checksum(object_store, unique_key):
    payload = bytes(range(256)) * 64
    expected_checksum = hashlib.sha256(payload).hexdigest()

    stored_checksum = object_store.put_bytes(unique_key, payload)
    retrieved = object_store.get_bytes(unique_key)
    metadata = object_store.head(unique_key)

    assert stored_checksum == expected_checksum
    assert retrieved == payload
    assert metadata["Metadata"]["sha256"] == expected_checksum
    assert metadata["ContentLength"] == len(payload)

    object_store.delete(unique_key)


def test_object_overwrite_updates_content(object_store, unique_key):
    object_store.put_bytes(unique_key, b"first version")
    object_store.put_bytes(unique_key, b"second version")

    assert object_store.get_bytes(unique_key) == b"second version"
    object_store.delete(unique_key)


def test_missing_object_returns_error(object_store, unique_key):
    from botocore.exceptions import ClientError

    with pytest.raises(ClientError):
        object_store.get_bytes(unique_key)

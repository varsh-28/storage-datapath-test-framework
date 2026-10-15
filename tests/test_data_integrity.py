import hashlib

from src.data_factory import deterministic_payload


def test_checksum_matches_expected_digest(fs_client):
    payload = b"integrity-check" * 4096
    fs_client.write_file("integrity.bin", payload)

    expected = hashlib.sha256(payload).hexdigest()
    actual = fs_client.checksum("integrity.bin")

    assert actual == expected


def test_large_payload_round_trip_and_checksum(fs_client):
    payload = deterministic_payload(4 * 1024 * 1024, seed=42)
    fs_client.write_file("large.bin", payload)

    assert fs_client.file_size("large.bin") == len(payload)
    assert fs_client.checksum("large.bin") == hashlib.sha256(payload).hexdigest()
    assert fs_client.read_file("large.bin") == payload


def test_corruption_is_detected_by_checksum(fs_client):
    original = b"original payload"
    fs_client.write_file("data.bin", original)
    original_checksum = fs_client.checksum("data.bin")

    fs_client.write_file("data.bin", b"modified payload")

    assert fs_client.checksum("data.bin") != original_checksum

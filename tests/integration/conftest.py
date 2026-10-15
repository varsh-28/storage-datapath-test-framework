import os
import uuid

import pytest

from src.object_storage_client import ObjectStorageClient


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires a running S3-compatible service")


@pytest.fixture(scope="session")
def object_store():
    if os.getenv("RUN_S3_TESTS", "0") != "1":
        pytest.skip("Set RUN_S3_TESTS=1 to run MinIO/S3 integration tests")

    client = ObjectStorageClient.from_env()
    client.ensure_bucket()
    return client


@pytest.fixture
def unique_key():
    return f"pytest/{uuid.uuid4().hex}.bin"

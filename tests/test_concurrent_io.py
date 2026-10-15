from concurrent.futures import ThreadPoolExecutor

from src.data_factory import deterministic_payload


def test_concurrent_independent_file_writes_and_reads(fs_client):
    items = {
        f"worker-{i}.bin": deterministic_payload(128 * 1024, seed=i)
        for i in range(12)
    }

    def write_one(item):
        name, payload = item
        fs_client.write_file(name, payload)
        return name

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(write_one, items.items()))

    def verify_one(item):
        name, expected = item
        actual = fs_client.read_file(name)
        return actual == expected

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(verify_one, items.items()))

    assert all(results)

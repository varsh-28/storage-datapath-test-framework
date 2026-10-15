
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import argparse
import hashlib
import json
import platform
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.data_factory import deterministic_payload
from src.object_storage_client import ObjectStorageClient


MIB = 1024 * 1024


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    index = max(0, int((percent / 100) * len(ordered) + 0.999999) - 1)
    return round(ordered[min(index, len(ordered) - 1)], 3)


def measure_phase(operation, items, workers: int, total_bytes: int):
    latencies = []

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for latency in pool.map(operation, items):
            latencies.append(latency)
    elapsed = time.perf_counter() - started

    return {
        "elapsed_seconds": round(elapsed, 4),
        "throughput_mib_per_sec": round(
            total_bytes / MIB / elapsed, 3
        ),
        "iops": round(len(items) / elapsed, 3),
        "latency_ms": {
            "min": round(min(latencies), 3),
            "mean": round(statistics.mean(latencies), 3),
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "max": round(max(latencies), 3),
        },
    }


def run_trial(store, trial: int, files: int, size_mib: int, workers: int):
    size_bytes = size_mib * MIB
    prefix = f"benchmark/{uuid.uuid4().hex}/"

    # Prepare payloads before timing the storage operations.
    items = [
        (
            f"{prefix}object-{i}.bin",
            deterministic_payload(size_bytes, seed=trial * 100000 + i),
        )
        for i in range(files)
    ]

    total_bytes = sum(len(payload) for _, payload in items)
    integrity = {"checked": 0, "failures": 0}

    try:
        def upload(item):
            key, payload = item
            start = time.perf_counter()
            checksum = store.put_bytes(key, payload)
            elapsed_ms = (time.perf_counter() - start) * 1000

            expected = hashlib.sha256(payload).hexdigest()
            if checksum != expected:
                raise AssertionError(f"Upload checksum mismatch: {key}")

            return elapsed_ms

        write_result = measure_phase(
            upload, items, workers, total_bytes
        )

        def download(item):
            key, original_payload = item
            start = time.perf_counter()
            received = store.get_bytes(key)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if hashlib.sha256(received).digest() != hashlib.sha256(
                original_payload
            ).digest():
                raise AssertionError(f"Download integrity failure: {key}")

            return elapsed_ms

        read_result = measure_phase(
            download, items, workers, total_bytes
        )

        integrity["checked"] = files

        return {
            "trial": trial,
            "files": files,
            "file_size_mib": size_mib,
            "workers": workers,
            "write": write_result,
            "read": read_result,
            "integrity": integrity,
        }

    finally:
        # Cleanup is deliberately excluded from benchmark timings.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(store.delete, [key for key, _ in items]))


def main():
    parser = argparse.ArgumentParser(
        description="Repeatable MinIO/S3 object-storage benchmark"
    )
    parser.add_argument("--files", type=int, default=20)
    parser.add_argument("--size-mib", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/benchmark-object-storage.json"),
    )
    args = parser.parse_args()

    if min(args.files, args.size_mib, args.workers, args.trials) < 1:
        parser.error("All numeric arguments must be positive")

    store = ObjectStorageClient.from_env()
    store.ensure_bucket()

    results = []

    for trial in range(1, args.trials + 1):
        result = run_trial(
            store,
            trial,
            args.files,
            args.size_mib,
            args.workers,
        )
        results.append(result)

        print(
            f"Trial {trial}/{args.trials}: "
            f"write={result['write']['throughput_mib_per_sec']} MiB/s, "
            f"read={result['read']['throughput_mib_per_sec']} MiB/s, "
            f"verified={result['integrity']['checked']}"
        )

    summary = {}
    for phase in ("write", "read"):
        summary[phase] = {
            "median_throughput_mib_per_sec": round(
                statistics.median(
                    result[phase]["throughput_mib_per_sec"]
                    for result in results
                ),
                3,
            ),
            "median_iops": round(
                statistics.median(
                    result[phase]["iops"] for result in results
                ),
                3,
            ),
            "median_latency_ms": {
                name: round(
                    statistics.median(
                        result[phase]["latency_ms"][name]
                        for result in results
                    ),
                    3,
                )
                for name in ("p50", "p95")
            },
        }

    report = {
        "storage_type": "S3-compatible object storage (MinIO)",
        "environment": {
            "platform": platform.platform(),
            "endpoint": "configured through S3_ENDPOINT_URL",
        },
        "configuration": vars(args) | {"output": str(args.output)},
        "summary": summary,
        "trials": results,
        "integrity_verified": all(
            result["integrity"]["checked"] == args.files
            and result["integrity"]["failures"] == 0
            for result in results
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nMedian results:")
    print(json.dumps(summary, indent=2))
    print(f"\nReport saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()

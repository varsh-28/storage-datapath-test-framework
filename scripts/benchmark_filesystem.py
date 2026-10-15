from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_factory import deterministic_payload
from src.filesystem_client import FileSystemClient

def percentile(values: list[float], p: float) -> float:
    """Calculate a nearest-rank percentile in milliseconds."""
    if not values:
        return 0.0

    ordered = sorted(values)
    index = max(0, int((p / 100) * len(ordered) + 0.999999) - 1)
    return ordered[min(index, len(ordered) - 1)] * 1000


def summarize(
    latencies: list[float],
    total_bytes: int,
    elapsed: float,
) -> dict:
    operations = len(latencies)

    return {
        "operations": operations,
        "total_bytes": total_bytes,
        "elapsed_seconds": round(elapsed, 4),
        "throughput_mib_per_sec": round(
            total_bytes / (1024 * 1024) / elapsed, 3
        ) if elapsed > 0 else 0.0,
        "iops": round(operations / elapsed, 2) if elapsed > 0 else 0.0,
        "latency_ms": {
            "min": round(min(latencies) * 1000, 3),
            "mean": round(statistics.mean(latencies) * 1000, 3),
            "p50": round(percentile(latencies, 50), 3),
            "p95": round(percentile(latencies, 95), 3),
            "max": round(max(latencies) * 1000, 3),
        },
    }


def run_benchmark(
    directory: Path,
    file_count: int,
    size_mib: int,
    workers: int,
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    client = FileSystemClient(directory)

    payload_size = size_mib * 1024 * 1024
    payload = deterministic_payload(payload_size, seed=2026)
    expected_checksum = __import__("hashlib").sha256(payload).hexdigest()

    filenames = [
        f"benchmark-{uuid.uuid4().hex}-{i}.bin"
        for i in range(file_count)
    ]

    def write_one(filename: str) -> float:
        start = time.perf_counter()
        client.write_file(filename, payload)
        return time.perf_counter() - start

    def read_one(filename: str) -> float:
        start = time.perf_counter()
        actual = client.read_file(filename)
        elapsed = time.perf_counter() - start

        if len(actual) != payload_size:
            raise AssertionError(f"Incorrect file size: {filename}")

        import hashlib
        if hashlib.sha256(actual).hexdigest() != expected_checksum:
            raise AssertionError(f"Data integrity failure: {filename}")

        return elapsed

    try:
        # Phase 1: concurrent writes
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            write_latencies = list(pool.map(write_one, filenames))
        write_elapsed = time.perf_counter() - start

        # Phase 2: concurrent reads and integrity verification
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            read_latencies = list(pool.map(read_one, filenames))
        read_elapsed = time.perf_counter() - start

        total_bytes = payload_size * file_count

        return {
            "configuration": {
                "storage_path": str(directory.resolve()),
                "files": file_count,
                "file_size_bytes": payload_size,
                "workers": workers,
                "write_uses_fsync": True,
                "read_checksum_validation": "SHA-256",
            },
            "write": summarize(
                write_latencies, total_bytes, write_elapsed
            ),
            "read": summarize(
                read_latencies, total_bytes, read_elapsed
            ),
            "integrity": {
                "verified_files": file_count,
                "failed_files": 0,
                "status": "PASS",
            },
            "notes": [
                "Write latency includes the client's file fsync.",
                "Read results may benefit from the operating system cache.",
                "Results describe this filesystem and environment, not a storage array.",
            ],
        }

    finally:
        # Remove only the files created by this benchmark run.
        for filename in filenames:
            path = directory / filename
            if path.exists():
                path.unlink()



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repeatable filesystem I/O benchmark"
    )
    parser.add_argument("--files", type=int, default=20)
    parser.add_argument("--size-mib", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/benchmark.json")
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help="Parent directory for temporary benchmark files",
    )
    args = parser.parse_args()

    if min(args.files, args.size_mib, args.workers, args.trials) < 1:
        parser.error(
            "--files, --size-mib, --workers, and --trials "
            "must be positive"
        )

    trial_results = []

    for trial_number in range(1, args.trials + 1):
        if args.directory:
            args.directory.mkdir(parents=True, exist_ok=True)
            temp_context = TemporaryDirectory(dir=args.directory)
        else:
            temp_context = TemporaryDirectory(
                prefix="storage-benchmark-"
            )

        with temp_context as temp_dir:
            result = run_benchmark(
                Path(temp_dir),
                args.files,
                args.size_mib,
                args.workers,
            )

        result["trial"] = trial_number
        trial_results.append(result)

        print(
            f"Trial {trial_number}/{args.trials}: "
            f"write={result['write']['throughput_mib_per_sec']} MiB/s, "
            f"read={result['read']['throughput_mib_per_sec']} MiB/s"
        )

    def median_metric(phase: str, metric: str) -> float:
        return round(
            statistics.median(
                result[phase][metric] for result in trial_results
            ),
            3,
        )

    summary = {}

    for phase in ("write", "read"):
        summary[phase] = {
            "median_throughput_mib_per_sec": median_metric(
                phase, "throughput_mib_per_sec"
            ),
            "median_iops": median_metric(phase, "iops"),
            "median_latency_ms": {
                percentile_name: round(
                    statistics.median(
                        result[phase]["latency_ms"][percentile_name]
                        for result in trial_results
                    ),
                    3,
                )
                for percentile_name in ("p50", "p95")
            },
        }

    report = {
        "configuration": {
            "files": args.files,
            "file_size_mib": args.size_mib,
            "workers": args.workers,
            "trials": args.trials,
        },
        "summary": summary,
        "trials": trial_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nMedian results across all trials:")
    print(json.dumps(summary, indent=2))
    print(f"\nReport saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()

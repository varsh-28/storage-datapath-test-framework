# Storage Data-Path Test Automation Framework

A Python-based framework for validating storage operations, data integrity, failure handling, concurrent I/O, and S3-compatible object storage. Includes repeatable performance benchmarks and automated test reporting.

## Overview

Storage systems must do more than accept read and write requests. They must preserve data integrity, handle invalid operations predictably, support concurrent workloads, and provide measurable performance.

This project demonstrates how to automate these validations using Python, pytest, filesystem operations, and MinIO's S3-compatible API.

### Key capabilities

- **Filesystem testing:** Validate file creation, reads, writes, overwrites, deletion, metadata, and invalid paths.
- **Data integrity:** Use SHA-256 checksums to detect unexpected content changes.
- **Failure handling:** Test missing files and objects, invalid inputs, and path-traversal attempts.
- **Concurrent I/O:** Exercise independent file operations using multiple workers.
- **Object-storage integration:** Upload, download, overwrite, and verify objects through an S3-compatible API.
- **Performance benchmarking:** Measure throughput, IOPS, and latency percentiles over repeated trials.
- **Test reporting:** Generate pytest results in JUnit XML and coverage reports.
- **CI automation:** Provide a GitHub Actions workflow for automated test execution.

## Architecture

```text
                Test Workloads
                      |
          +-----------+-----------+
          |                       |
   Filesystem Tests         Object Storage Tests
          |                       |
   FileSystemClient        ObjectStorageClient
          |                       |
   Local File System        MinIO / S3 API
          |                       |
          +-----------+-----------+
                      |
             Validation Layer
                      |
       Checksums, Assertions, Error Checks
                      |
              Pytest Reports
                      |
          +-----------+-----------+
          |                       |
      Test Results          Coverage Reports

       Benchmark Scripts
          |           |
     Filesystem      Object Storage
     Throughput      Throughput
     IOPS/Latency     IOPS/Latency
```

## Technology stack

| Technology | Purpose |
|---|---|
| Python | Test and benchmark implementation |
| pytest | Test execution and assertions |
| SHA-256 | Content-integrity validation |
| MinIO | Local S3-compatible object storage |
| Docker Compose | Local service setup |
| pytest-cov | Code coverage |
| GitHub Actions | CI automation |

## Repository structure

```text
storage-datapath-test-framework/
├── src/
│   ├── filesystem_client.py
│   ├── object_storage_client.py
│   └── data_factory.py
├── tests/
│   ├── integration/
│   │   └── test_object_storage.py
│   ├── test_concurrent_io.py
│   ├── test_data_integrity.py
│   ├── test_failure_handling.py
│   ├── test_file_metadata.py
│   └── test_file_operations.py
├── scripts/
│   ├── benchmark_filesystem.py
│   └── benchmark_object_storage.py
├── reports/
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.11 or later, compatible with the installed dependencies
- Docker Desktop or another working Docker environment
- Git
- A Windows, Linux, or macOS development environment

Commands below use PowerShell on Windows.

## Installation

Clone the repository:

```powershell
git clone <YOUR_REPOSITORY_URL>
cd storage-datapath-test-framework
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Start object storage

Start the configured MinIO service using Docker Compose:

```powershell
docker compose up -d
docker compose ps
```

The default local endpoints are:

- S3 API: `http://127.0.0.1:9000`
- Web console: `http://127.0.0.1:9001`

Use the credentials configured for your local container. Never expose real credentials in source code or commit them to Git.

Verify that the service is responding:

```powershell
Invoke-WebRequest http://127.0.0.1:9000/minio/health/live
```

If the container image or compose configuration changes, review its source and use a trusted, maintained image for long-term use.

## Configure integration tests

Set the environment variables in your PowerShell session:

```powershell
$env:S3_ENDPOINT_URL = "http://127.0.0.1:9000"
$env:S3_ACCESS_KEY = "minioadmin"
$env:S3_SECRET_KEY = "minioadmin"
$env:S3_BUCKET = "storage-test-bucket"
$env:RUN_S3_TESTS = "1"
```

These example credentials are for a local development environment only. Replace them with appropriately secured credentials outside local testing.

## Run the tests

Run the complete test suite:

```powershell
python -m pytest tests -v
```

Run only filesystem-focused tests:

```powershell
python -m pytest tests/test_file_operations.py tests/test_data_integrity.py tests/test_failure_handling.py tests/test_file_metadata.py tests/test_concurrent_io.py -v
```

Run object-storage integration tests:

```powershell
python -m pytest tests/integration/test_object_storage.py -v
```

Generate coverage and test reports:

```powershell
python -m pytest tests -v --cov=src --cov-report=term-missing --cov-report=xml --junitxml=reports/junit.xml
```

The object-storage tests require a running, correctly configured MinIO service when enabled.

## Performance benchmarks

Both benchmark scripts execute repeated trials and save their results as JSON.

### Filesystem benchmark

Small files:

```powershell
python scripts/benchmark_filesystem.py --files 100 --size-mib 1 --workers 8 --trials 5 --output reports/benchmark-repeatable.json
```

Large files:

```powershell
python scripts/benchmark_filesystem.py --files 10 --size-mib 16 --workers 2 --trials 5 --output reports/benchmark-large-repeatable.json
```

### Object-storage benchmark

Small objects:

```powershell
python scripts/benchmark_object_storage.py --files 100 --size-mib 1 --workers 8 --trials 5 --output reports/benchmark-object-small.json
```

Large objects:

```powershell
python scripts/benchmark_object_storage.py --files 10 --size-mib 16 --workers 2 --trials 5 --output reports/benchmark-object-large.json
```

### Metrics

- **Throughput:** Amount of data transferred per second, reported in MiB/s.
- **IOPS:** Completed operations per second.
- **p50 latency:** Median operation latency.
- **p95 latency:** Latency at or below which approximately 95% of measured operations completed.
- **Integrity verification:** Confirms that downloaded content matches the expected SHA-256 digest.

Each workload is run five times. The summary reports the median of the per-trial metrics. Benchmark results can vary with hardware, caching, background activity, concurrency, and container overhead.

## Observed object-storage benchmark results

Environment: Windows, Python 3.13.7, local MinIO container. Five trials per workload.

| Workload | Operation | Median throughput | Median IOPS | Median p95 latency |
|---|---|---:|---:|---:|
| 100 × 1 MiB, 8 workers | Write | 90.633 MiB/s | 90.633 | 108.600 ms |
| 100 × 1 MiB, 8 workers | Read | 110.716 MiB/s | 110.716 | 87.391 ms |
| 10 × 16 MiB, 2 workers | Write | 70.917 MiB/s | 4.432 | 516.086 ms |
| 10 × 16 MiB, 2 workers | Read | 105.160 MiB/s | 6.572 | 288.941 ms |

All objects passed the benchmark's integrity verification in each reported trial.

These are local development measurements, not claims about enterprise storage performance. The workloads differ in object size and worker count, so the results should not be used to isolate the effect of object size alone.

## Current validation status

Latest recorded full test run:

- 16 tests passed
- 1 test skipped
- 83% total code coverage
- 3 MinIO integration tests passed

The skipped test checks POSIX-specific permission behavior that is not directly supported by the same semantics on Windows.

These results describe the current local run. CI results should be recorded separately when verified.

## Scope and limitations

Currently implemented:

- Local filesystem operations and metadata checks
- Concurrent operations on independent files
- SHA-256 data-integrity checks
- Invalid-input and missing-resource tests
- S3-compatible object-storage integration
- Repeatable client-side performance measurements

Not yet implemented:

- Physical storage-array or SAN hardware validation
- Fibre Channel or iSCSI protocol testing
- NFS or SMB network-filesystem validation
- Crash-durability and power-loss testing
- Kubernetes persistent-volume integration
- Cross-platform validation on Linux and Windows

## Future improvements

- Add Linux CI jobs and platform-specific permission tests.
- Add controlled performance comparisons with fixed workload parameters.
- Extend failure-injection tests and concurrent overwrite scenarios.
- Add network-filesystem and block-storage integration in a suitable lab.
- Publish benchmark trends and regression thresholds in CI.

## What this project demonstrates

This project demonstrates practical skills in Python test automation, pytest, storage data-path validation, data integrity, concurrent I/O, S3-compatible APIs, Docker-based testing, performance metrics, and CI workflows.

It is a learning and portfolio framework rather than a replacement for vendor-specific storage qualification suites.

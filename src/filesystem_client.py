from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath


class FileSystemClient:
    """Safe, small filesystem adapter for repeatable data-path tests.

    Writes are staged in the target directory and atomically renamed into place.
    This avoids readers observing a partially written file, but does not claim
    hardware-level durability or protection against power loss.
    """

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir).expanduser().resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, filename: str) -> Path:
        if not filename or "\x00" in filename:
            raise ValueError("filename must be non-empty and contain no NUL bytes")

        # Accept only a single filename, not a path supplied by the caller.
        candidate = PurePosixPath(filename)
        if candidate.is_absolute() or len(candidate.parts) != 1 or filename in {".", ".."}:
            raise ValueError("filename must be a simple filename, not a path")

        path = (self.storage_dir / filename).resolve()
        if path.parent != self.storage_dir:
            raise ValueError("filename resolves outside the storage directory")
        return path

    def write_file(self, filename: str, data: bytes) -> Path:
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        destination = self._resolve(filename)
        fd, temp_name = tempfile.mkstemp(prefix=".storage-test-", dir=self.storage_dir)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, destination)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
        return destination

    def read_file(self, filename: str) -> bytes:
        return self._resolve(filename).read_bytes()

    def delete_file(self, filename: str) -> None:
        self._resolve(filename).unlink()

    def file_exists(self, filename: str) -> bool:
        return self._resolve(filename).is_file()

    def checksum(self, filename: str, algorithm: str = "sha256") -> str:
        digest = hashlib.new(algorithm)
        with self._resolve(filename).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def file_size(self, filename: str) -> int:
        return self._resolve(filename).stat().st_size

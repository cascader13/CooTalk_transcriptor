import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aioboto3
import aiofiles
from botocore.exceptions import ClientError

from .errors import AudioNotFoundError


class AudioStorage:
    def __init__(
        self,
        bucket: str,
        *,
        access_key: str,
        secret_key: str,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        prefix: str = "",
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.endpoint_url = endpoint_url
        self.session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

    def _client(self):
        return self.session.client("s3", endpoint_url=self.endpoint_url)

    def _key(self, storage_key: str) -> str:
        if not storage_key:
            raise ValueError("storageKey must not be empty")
        return f"{self.prefix}/{storage_key.lstrip('/')}" if self.prefix else storage_key

    async def is_ready(self) -> bool:
        try:
            async with self._client() as s3:
                await s3.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False

    async def download(self, storage_key: str, destination: Path) -> None:
        try:
            async with self._client() as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=self._key(storage_key))
                body = response["Body"]
                try:
                    async with aiofiles.open(destination, "wb") as output:
                        while chunk := await body.read(1024 * 1024):
                            await output.write(chunk)
                finally:
                    body.close()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise AudioNotFoundError(storage_key) from exc
            raise

    @staticmethod
    async def convert_to_wav(source: Path, destination: Path) -> None:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-nostdin", "-v", "error", "-i", str(source),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-y", str(destination),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Audio conversion failed: {message}")

    @asynccontextmanager
    async def wav_for_gigaam(self, storage_key: str) -> AsyncIterator[Path]:
        self._key(storage_key)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source_audio"
            wav_path = Path(directory) / "input.wav"
            await self.download(storage_key, source)
            await self.convert_to_wav(source, wav_path)
            yield wav_path

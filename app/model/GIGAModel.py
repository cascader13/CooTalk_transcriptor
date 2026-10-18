from transformers import AutoModel
from .base import Model
import enum
import os

import asyncio
from pathlib import Path
import shutil
import sys


def configure_ffmpeg():
    if shutil.which("ffmpeg"):
        return

    if os.name == "nt":
        conda_ffmpeg_dir = Path(sys.prefix) / "Library" / "bin"
        if (conda_ffmpeg_dir / "ffmpeg.exe").is_file():
            os.environ["PATH"] = str(conda_ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")
            return

    raise FileNotFoundError("FFmpeg is not installed or not available in PATH")


class HealthStatus(enum.Enum):
    READY = 0,
    WORKING = 1,
    ERROR = 2
    def __str__(self):
        return self.name




class GIGAModel(Model):
    def __init__(self):
        configure_ffmpeg()
        self.MODEL_PATH = Path(__file__).resolve().parent / "GigaAM-v3"
        self.model = AutoModel.from_pretrained(self.MODEL_PATH, trust_remote_code=True, local_files_only=True, low_cpu_mem_usage=False)
        self.model.eval()
        self._status = HealthStatus.READY


    async def transcribe(self, audio_path):
        self._status = HealthStatus.WORKING
        print(audio_path)
        try:
            segments = await asyncio.to_thread(
                self.model.transcribe_longform,
                audio_path,
            )
            text = " ".join(
                segment["transcription"] for segment in segments
            )
        finally:
            self._status = HealthStatus.READY

        return text
        
    def status(self):
        return self._status

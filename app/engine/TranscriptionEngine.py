from .base import Engine
import asyncio
from model.GIGAModel import HealthStatus

class TranscriptionEngine(Engine):
    def __init__(self, model):
        self.model = model

    @property
    def model_name(self):
        return "GigaAM-v3"

    def is_ready(self):
        return self.model.status() == HealthStatus.READY



    async def transcribe(self, audio_path):
        if self.model.status() == HealthStatus.ERROR:
            raise Exception("Model is unavailable")
        elif self.model.status() == HealthStatus.READY:
            return await self.model.transcribe(audio_path)
        raise Exception("Model is busy")
            



    

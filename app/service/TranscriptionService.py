import asyncio
import logging
import time
import wave
from pathlib import Path

import grpc
from generated import transcription_pb2, transcription_pb2_grpc
from storage.errors import AudioNotFoundError


logger = logging.getLogger(__name__)


class TranscriptionServiceServicer(transcription_pb2_grpc.TranscriptionServiceServicer):
    def __init__(self, storage, engine, result_receiver):
        self.storage = storage
        self.engine = engine
        self.result_receiver = result_receiver
        self._processing_lock = asyncio.Lock()
        self._tasks = set()

    async def AddTranscriptionTask(self, request, context):
        if not request.taskId:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "taskId must not be empty")
        if not request.storageKey:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "storageKey must not be empty")

        task = asyncio.create_task(
            self._process_task(request.taskId, request.storageKey),
            name=f"transcription-{request.taskId}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return transcription_pb2.Accepted()

    def _task_done(self, task):
        self._tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Failed to deliver a transcription result")

    async def _process_task(self, task_id, storage_key):
        async with self._processing_lock:
            start = time.perf_counter()
            try:
                async with self.storage.wav_for_gigaam(storage_key) as audio_path:
                    audio_duration = await asyncio.to_thread(self._wav_duration, audio_path)
                    text = await self.engine.transcribe(str(audio_path))

                processing_time = time.perf_counter() - start
                result = transcription_pb2.TranscriptionResult(
                    taskId=task_id,
                    success=transcription_pb2.TranscriptionOutput(
                        text=text,
                        model=self.engine.model_name,
                        processingTimeSeconds=processing_time,
                        audioDurationSeconds=audio_duration,
                        realTimeFactor=(processing_time / audio_duration if audio_duration > 0 else 0.0),
                    ),
                )
            except AudioNotFoundError:
                result = self._failure(task_id, "NOT_FOUND", f"Audio '{storage_key}' was not found")
            except ValueError as exc:
                result = self._failure(task_id, "INVALID_ARGUMENT", str(exc))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Transcription task %s failed", task_id)
                result = self._failure(task_id, "INTERNAL", str(exc))

        await self.result_receiver.ReturnTranscriptionResult(result)

    @staticmethod
    def _wav_duration(audio_path):
        with wave.open(str(Path(audio_path)), "rb") as audio:
            frame_rate = audio.getframerate()
            return audio.getnframes() / frame_rate if frame_rate else 0.0

    @staticmethod
    def _failure(task_id, code, message):
        return transcription_pb2.TranscriptionResult(
            taskId=task_id,
            failure=transcription_pb2.TranscriptionError(code=code, message=message),
        )

    async def wait_for_pending_tasks(self):
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

import asyncio
import tempfile
import unittest
import wave
from contextlib import asynccontextmanager
from pathlib import Path

import grpc

from generated import transcription_pb2, transcription_pb2_grpc
from service.TranscriptionService import TranscriptionServiceServicer
from storage.errors import AudioNotFoundError


class FakeStorage:
    def __init__(self):
        self.requested = None

    @asynccontextmanager
    async def wav_for_gigaam(self, storage_key):
        self.requested = storage_key
        if storage_key == "missing.opus":
            raise AudioNotFoundError(storage_key)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.wav"
            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16_000)
                audio.writeframes(b"\0\0" * 32_000)
            yield path


class FakeEngine:
    model_name = "GigaAM-v3"

    async def transcribe(self, path):
        return "Тестовая расшифровка"


class FakeResultReceiver:
    def __init__(self):
        self.results = asyncio.Queue()

    async def ReturnTranscriptionResult(self, result):
        await self.results.put(result)
        return transcription_pb2.Accepted()


class TranscriptionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = FakeStorage()
        self.receiver = FakeResultReceiver()
        self.servicer = TranscriptionServiceServicer(
            self.storage, FakeEngine(), self.receiver
        )
        self.server = grpc.aio.server()
        transcription_pb2_grpc.add_TranscriptionServiceServicer_to_server(
            self.servicer, self.server
        )
        port = self.server.add_insecure_port("127.0.0.1:0")
        await self.server.start()
        self.channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
        self.stub = transcription_pb2_grpc.TranscriptionServiceStub(self.channel)

    async def asyncTearDown(self):
        await self.servicer.wait_for_pending_tasks()
        await self.channel.close()
        await self.server.stop(0)

    async def submit(self, task_id="task-1", storage_key="folder/recording.opus"):
        return await self.stub.AddTranscriptionTask(
            transcription_pb2.TranscriptionTask(
                taskId=task_id,
                storageKey=storage_key,
            )
        )

    async def test_task_is_accepted_and_success_is_returned(self):
        response = await self.submit()
        self.assertIsInstance(response, transcription_pb2.Accepted)

        result = await asyncio.wait_for(self.receiver.results.get(), timeout=1)
        self.assertEqual(result.taskId, "task-1")
        self.assertEqual(result.WhichOneof("outcome"), "success")
        self.assertEqual(result.success.text, "Тестовая расшифровка")
        self.assertEqual(result.success.model, "GigaAM-v3")
        self.assertAlmostEqual(result.success.audioDurationSeconds, 2.0)
        self.assertGreaterEqual(result.success.processingTimeSeconds, 0.0)
        self.assertGreaterEqual(result.success.realTimeFactor, 0.0)
        self.assertEqual(self.storage.requested, "folder/recording.opus")

    async def test_missing_file_is_returned_as_failure(self):
        await self.submit(storage_key="missing.opus")

        result = await asyncio.wait_for(self.receiver.results.get(), timeout=1)
        self.assertEqual(result.WhichOneof("outcome"), "failure")
        self.assertEqual(result.failure.code, "NOT_FOUND")

    async def test_empty_task_id_is_rejected(self):
        with self.assertRaises(grpc.aio.AioRpcError) as error:
            await self.submit(task_id="")
        self.assertEqual(error.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertIsNone(self.storage.requested)

    async def test_empty_storage_key_is_rejected(self):
        with self.assertRaises(grpc.aio.AioRpcError) as error:
            await self.submit(storage_key="")
        self.assertEqual(error.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertIsNone(self.storage.requested)

import asyncio
import grpc
from storage.storage import AudioStorage
from engine.TranscriptionEngine import TranscriptionEngine

from generated import transcription_pb2_grpc
from service.TranscriptionService import TranscriptionServiceServicer
from model.GIGAModel import GIGAModel
from dotenv import load_dotenv
import os
from pathlib import Path


class ResultReceiverClient:
    def __init__(self, stub, timeout):
        self.stub = stub
        self.timeout = timeout

    async def ReturnTranscriptionResult(self, result):
        return await self.stub.ReturnTranscriptionResult(result, timeout=self.timeout)


async def serve():
    load_dotenv(Path(__file__).with_name(".env"))

    required = ("BUCKET", "ACCESS_KEY", "SECRET_KEY", "ENDPOINT", "RESULT_RECEIVER_TARGET")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)}")

    server = grpc.aio.server()

    storage = AudioStorage(
        bucket=os.environ["BUCKET"],
        access_key=os.environ["ACCESS_KEY"],
        secret_key=os.environ["SECRET_KEY"],
        endpoint_url=os.environ["ENDPOINT"],
        region_name=os.getenv("REGION") or None,
        prefix=os.getenv("S3_PREFIX", ""),
    )
    model = GIGAModel()
    engine = TranscriptionEngine(model=model)
    


    result_channel = grpc.aio.insecure_channel(os.environ["RESULT_RECEIVER_TARGET"])
    result_receiver_stub = transcription_pb2_grpc.TranscriptionResultReceiverStub(result_channel)
    result_receiver = ResultReceiverClient(
        result_receiver_stub,
        timeout=float(os.getenv("RESULT_RECEIVER_TIMEOUT_SECONDS", "10")),
    )
    servicer = TranscriptionServiceServicer(
        storage=storage,
        engine=engine,
        result_receiver=result_receiver,
    )

    transcription_pb2_grpc.add_TranscriptionServiceServicer_to_server(
        servicer,
        server
    )

    bind_address = os.getenv("GRPC_BIND", "[::]:50051")
    server.add_insecure_port(bind_address)

    await server.start()

    print(f"gRPC server started on {bind_address}")

    try:
        await server.wait_for_termination()
    finally:
        await servicer.wait_for_pending_tasks()
        await result_channel.close()


if __name__ == "__main__":
    asyncio.run(serve())

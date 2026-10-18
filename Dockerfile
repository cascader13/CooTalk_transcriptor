FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install matching CPU builds of PyTorch, TorchAudio, and TorchCodec.
RUN python -m pip install --no-cache-dir \
    torch==2.11.0 \
    torchaudio==2.11.0 \
    torchcodec==0.17.0 \
    --index-url https://download.pytorch.org/whl/cpu

WORKDIR /srv
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system app && useradd --system --gid app --home-dir /home/app --create-home app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app

COPY --chown=app:app app/ /srv/app/
WORKDIR /srv/app
USER app

EXPOSE 50051
CMD ["python", "-u", "main.py"]

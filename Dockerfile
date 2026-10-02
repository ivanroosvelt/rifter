FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
# yt-dlp needs a JS runtime for YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
# ponytail: unpinned on purpose, YouTube breaks old yt-dlp; rebuild with --no-cache to update
RUN pip install --no-cache-dir "yt-dlp[default]"
WORKDIR /srv
COPY server.py index.html ./
CMD ["python", "-u", "server.py"]

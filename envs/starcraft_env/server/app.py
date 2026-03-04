# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the StarCraft Environment.

Usage:
    PYTHONPATH=src:envs uvicorn envs.starcraft_env.server.app:app --host 0.0.0.0 --port 8000

Environment variables:
    APP_FILE: Path to StarCraft.exe (default: "/apps/Starcraft/StarCraft.exe")
    WINDOW_TITLE: Window title to find (default: "Brood War")
"""

import asyncio
import io
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi.responses import HTMLResponse, StreamingResponse
from openenv.core.env_server import create_app

from ..models import StarCraftAction, StarCraftObservation
from .starcraft_environment import StarCraftEnvironment

app_file = os.getenv("APP_FILE", "/apps/Starcraft/StarCraft.exe")
window_title = os.getenv("WINDOW_TITLE", "Brood War")

# Thread pool with ONE worker to ensure thread affinity for GUI/Wine interactions
executor = ThreadPoolExecutor(max_workers=1)


def create_starcraft_environment():
    """Factory function that creates StarCraftEnvironment with config."""
    return StarCraftEnvironment()


app = create_app(
    create_starcraft_environment,
    StarCraftAction,
    StarCraftObservation,
    env_name="starcraft_env",
)

# Cache for the environment instance used in stream endpoints
_stream_env = None


def _get_stream_env():
    global _stream_env
    if _stream_env is None:
        _stream_env = StarCraftEnvironment()
    return _stream_env


@app.get("/stream")
async def stream_mjpeg():
    """MJPEG stream for real-time viewing."""

    async def generate():
        while True:
            try:
                loop = asyncio.get_event_loop()
                img = await loop.run_in_executor(
                    executor, lambda: _get_stream_env().capture_screen()
                )

                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                buffer.seek(0)
                yield (
                    b"\r\n--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + buffer.read()
                    + b"\r\n"
                )
                await asyncio.sleep(0.1)  # 10 FPS
            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(0.5)

    return StreamingResponse(
        generate(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/viewer")
async def viewer():
    """HTML viewer page."""
    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
<head>
    <title>StarCraft Environment</title>
    <style>
        body { margin: 0; padding: 20px; background: #1a1a1a; color: #fff; font-family: sans-serif; }
        .container { max-width: 1000px; margin: 0 auto; text-align: center; }
        h1 { margin-bottom: 20px; }
        img { border: 2px solid #333; max-width: 100%; }
        .info { margin-top: 20px; padding: 15px; background: #2a2a2a; border-radius: 8px; }
        .live { color: #4caf50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>StarCraft Environment</h1>
        <img src="/stream" alt="Stream" />
        <div class="info">
            <p>Status: <span class="live">LIVE</span></p>
            <p>Stream: <code>http://localhost:8000/stream</code></p>
        </div>
    </div>
</body>
</html>
    """
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

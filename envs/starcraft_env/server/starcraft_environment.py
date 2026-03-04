# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
StarCraft Environment Server Implementation.

Wraps StarCraft: Brood War running under Wine and exposes it via
the OpenEnv Environment interface.
"""

import base64
import io
import os
import subprocess
import time
import uuid
from typing import Any, Optional

from openenv.core.env_server import Environment
from PIL import Image

from ..models import StarCraftAction, StarCraftObservation, StarCraftState


class StarCraftEnvironment(Environment):
    def __init__(self):
        super().__init__()
        self._state = StarCraftState()
        self._wine_process = None
        self._syncinput_process = None
        self._app_process = None

        # Default config
        self.app_path = os.environ.get("APP_FILE", "/apps/Starcraft/StarCraft.exe")
        self.window_name = os.environ.get("WINDOW_TITLE", "Brood War")

        # Screen capture
        self.monitor = {"top": 0, "left": 0, "width": 640, "height": 480}

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> StarCraftObservation:
        """Reset the environment (restart game if needed)."""
        self._cleanup()
        self._start_game()

        self._state.episode_id = episode_id or str(uuid.uuid4())
        self._state.step_count = 0
        self._state.app_running = True

        return self._capture_observation()

    def step(
        self,
        action: StarCraftAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> StarCraftObservation:
        """Execute action and return observation."""
        if not self._state.app_running:
            return self.reset()

        self._execute_action(action)
        self._state.step_count += 1

        return self._capture_observation()

    @property
    def state(self) -> StarCraftState:
        return self._state

    def _execute_action(self, action: StarCraftAction):
        """Execute low-level input action."""
        # We can use xdotool or the compiled syncinput.exe
        # Using xdotool for simplicity in this initial port as it is standard installed in Dockerfile

        if action.action_type == "noop":
            return

        if action.action_type == "key":
            key = action.key
            if key == "Return":
                key = "Return"
            # Map common keys if needed
            subprocess.run(["xdotool", "key", key], check=False)

        elif action.action_type == "mouse":
            # Convert normalized coordinates to pixels
            x = int(action.x * 640)
            y = int(action.y * 480)

            subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=False)

            if action.mouse_state == "click":
                button = 1  # Left
                if action.button == "right":
                    button = 3
                subprocess.run(["xdotool", "click", str(button)], check=False)

    def capture_screen(self) -> Image.Image:
        """Capture screen using ffmpeg (x11grab) as suggested."""
        try:
            # Command to grab one frame from X11 display
            cmd = [
                "ffmpeg",
                "-f",
                "x11grab",
                "-video_size",
                "640x480",
                "-framerate",
                "30",
                "-y",  # overwrite
                "-i",
                os.environ.get("DISPLAY", ":0"),
                "-vframes",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",  # output to pipe
            ]

            # Run ffmpeg
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Load image from stdout
            return Image.open(io.BytesIO(result.stdout)).convert("RGB")

        except Exception as e:
            # Fallback to red screen if capture fails
            print(f"FFmpeg capture failed: {e}")
            return Image.new("RGB", (640, 480), color="red")

    def _capture_observation(self) -> StarCraftObservation:
        """Capture screen and return observation."""
        try:
            img = self.capture_screen()

            # Encode to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return StarCraftObservation(
                screen_image=f"data:image/png;base64,{img_str}",
                screen_shape=[480, 640, 3],
                success=True,
            )
        except Exception as e:
            print(f"Error in _capture_observation: {e}")
            return StarCraftObservation(success=False, error=str(e))

    def _start_game(self):
        """Start the StarCraft game process."""
        # Start Wine process in background
        # We assume Xvfb is running by supervisor
        cmd = ["wine", self.app_path]

        self._app_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "DISPLAY": ":0"},
        )

        # Wait a bit for it to start
        time.sleep(5)

        # Launch syncinput helper if we were using it for direct memory access or hook
        # For now, relying on xdotool

    def _cleanup(self):
        """Kill game processes."""
        if self._app_process:
            self._app_process.terminate()
            try:
                self._app_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._app_process.kill()

        subprocess.run(["pkill", "-9", "wine"], check=False)
        subprocess.run(["pkill", "-9", "StarCraft.exe"], check=False)

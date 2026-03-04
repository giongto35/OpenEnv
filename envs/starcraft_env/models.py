# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import List, Optional

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


class StarCraftAction(Action):
    """
    Action for StarCraft environment.
    Supports key presses and mouse clicks.
    """

    action_type: str  # "key", "mouse", "noop"

    # Key action
    key: Optional[str] = None

    # Mouse action
    x: Optional[float] = None  # Normalized 0-1
    y: Optional[float] = None  # Normalized 0-1
    button: str = "left"  # "left", "right", "middle"
    mouse_state: str = "click"  # "click", "down", "up", "move"


class StarCraftObservation(Observation):
    """
    Observation for StarCraft environment.
    Returns screen capture and game status.
    """

    screen_image: Optional[str] = None  # Base64 encoded PNG
    screen_shape: List[int] = Field(default_factory=lambda: [480, 640, 3])

    # Additional state info
    game_pixel_similarity: float = 0.0  # Change detection

    # Status
    success: bool = True
    error: Optional[str] = None


class StarCraftState(State):
    """
    State of the StarCraft environment.
    """

    step_count: int = 0
    episode_id: str = ""
    app_running: bool = False

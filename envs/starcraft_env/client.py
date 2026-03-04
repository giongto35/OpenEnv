# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""StarCraft Environment Client."""

from __future__ import annotations

from typing import Any, Dict

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import StarCraftAction, StarCraftObservation, StarCraftState


class StarCraftEnv(EnvClient[StarCraftAction, StarCraftObservation, StarCraftState]):
    """Client for StarCraft: Brood War environment running via Wine/Xvfb in Docker."""

    def _step_payload(self, action: StarCraftAction) -> Dict[str, Any]:
        payload = {"action_type": action.action_type}
        if action.action_type == "key":
            payload["key"] = action.key
        elif action.action_type == "mouse":
            payload.update(
                {
                    "x": action.x,
                    "y": action.y,
                    "button": action.button,
                    "mouse_state": action.mouse_state,
                }
            )
        return payload

    def _parse_result(
        self, payload: Dict[str, Any]
    ) -> StepResult[StarCraftObservation]:
        obs_data = payload.get("observation", {})
        obs = StarCraftObservation(
            screen_image=obs_data.get("screen_image"),
            screen_shape=obs_data.get("screen_shape", [480, 640, 3]),
            game_pixel_similarity=obs_data.get("game_pixel_similarity", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> StarCraftState:
        return StarCraftState(
            step_count=payload.get("step_count", 0),
            episode_id=payload.get("episode_id", ""),
            app_running=payload.get("app_running", False),
        )

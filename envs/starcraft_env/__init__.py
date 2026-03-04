# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
StarCraft: Brood War Environment for OpenEnv.

Runs StarCraft inside a Wine container with virtual X server (Xvfb).
Exposes keyboard/mouse input actions and returns screen captures as observations.

Example:
    >>> from envs.starcraft_env import StarCraftEnv, StarCraftAction
    >>>
    >>> env = StarCraftEnv(base_url="http://localhost:8000")
    >>> result = env.reset()
    >>> result = env.step(StarCraftAction(action_type="key", key="Return"))
    >>> print(result.observation.screen_image[:30])  # base64 PNG
    >>> env.close()
"""

from .client import StarCraftEnv
from .models import StarCraftAction, StarCraftObservation, StarCraftState

__all__ = ["StarCraftEnv", "StarCraftAction", "StarCraftObservation", "StarCraftState"]

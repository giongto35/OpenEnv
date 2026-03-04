# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for StarCraft environment models, server logic, and client logic.

Integration tests that require Wine/game files are skipped with a clear reason.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add project root so `from envs.starcraft_env import ...` resolves correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from envs.starcraft_env import (
    StarCraftAction,
    StarCraftEnv,
    StarCraftObservation,
    StarCraftState,
)
from envs.starcraft_env.server.starcraft_environment import StarCraftEnvironment
from openenv.core.client_types import StepResult


class TestStarCraftModels:
    """Test StarCraft data models (pure Pydantic validation, no game required)."""

    def test_key_action_creation(self):
        """Test StarCraftAction with action_type='key' stores key correctly."""
        action = StarCraftAction(action_type="key", key="Return")
        assert action.action_type == "key"
        assert action.key == "Return"

    def test_mouse_action_creation(self):
        """Test StarCraftAction with action_type='mouse' stores all mouse fields."""
        action = StarCraftAction(
            action_type="mouse",
            x=0.5,
            y=0.5,
            button="left",
            mouse_state="click",
        )
        assert action.action_type == "mouse"
        assert action.x == 0.5
        assert action.y == 0.5
        assert action.button == "left"
        assert action.mouse_state == "click"

    def test_noop_action_creation(self):
        """Test StarCraftAction with action_type='noop' requires no other fields."""
        action = StarCraftAction(action_type="noop")
        assert action.action_type == "noop"
        assert action.key is None
        assert action.x is None
        assert action.y is None

    def test_observation_defaults(self):
        """Test StarCraftObservation has correct default field values."""
        obs = StarCraftObservation()
        assert obs.screen_image is None
        assert obs.screen_shape == [480, 640, 3]
        assert obs.game_pixel_similarity == 0.0
        assert obs.success is True
        assert obs.error is None

    def test_observation_with_image(self):
        """Test StarCraftObservation stores base64 image string."""
        obs = StarCraftObservation(screen_image="data:image/png;base64,abc123")
        assert obs.screen_image == "data:image/png;base64,abc123"

    def test_observation_failure_mode(self):
        """Test StarCraftObservation can represent a failure state."""
        obs = StarCraftObservation(success=False, error="capture failed")
        assert obs.success is False
        assert obs.error == "capture failed"

    def test_state_defaults(self):
        """Test StarCraftState has correct default field values."""
        state = StarCraftState()
        assert state.step_count == 0
        assert state.episode_id == ""
        assert state.app_running is False

    def test_state_with_values(self):
        """Test StarCraftState stores explicit values correctly."""
        state = StarCraftState(step_count=5, episode_id="ep-001", app_running=True)
        assert state.step_count == 5
        assert state.episode_id == "ep-001"
        assert state.app_running is True

    def test_mouse_action_right_button(self):
        """Test StarCraftAction supports right mouse button."""
        action = StarCraftAction(action_type="mouse", x=0.3, y=0.7, button="right")
        assert action.button == "right"

    def test_mouse_action_move_state(self):
        """Test StarCraftAction supports 'move' mouse_state (no click)."""
        action = StarCraftAction(action_type="mouse", x=0.1, y=0.2, mouse_state="move")
        assert action.mouse_state == "move"


class TestStarCraftEnvironment:
    """Test StarCraftEnvironment server logic without starting the actual game."""

    @pytest.fixture
    def env(self):
        """Create StarCraftEnvironment with _start_game and _cleanup mocked out."""
        environment = StarCraftEnvironment()
        # Prevent any real subprocess calls during tests
        environment._start_game = MagicMock()
        environment._cleanup = MagicMock()
        # Also mock _capture_observation to avoid ffmpeg/X11 calls
        environment._capture_observation = MagicMock(
            return_value=StarCraftObservation(screen_image=None, success=True)
        )
        return environment

    def test_reset_sets_app_running_true(self, env):
        """Test reset() marks the app as running in state."""
        env.reset()
        assert env.state.app_running is True

    def test_reset_zeroes_step_count(self, env):
        """Test reset() resets step_count to 0."""
        # Manually advance step count before reset
        env._state.step_count = 99
        env.reset()
        assert env.state.step_count == 0

    def test_reset_sets_episode_id(self, env):
        """Test reset() assigns a non-empty episode_id."""
        env.reset()
        assert env.state.episode_id != ""

    def test_reset_accepts_custom_episode_id(self, env):
        """Test reset() uses provided episode_id when given."""
        env.reset(episode_id="my-episode-42")
        assert env.state.episode_id == "my-episode-42"

    def test_step_increments_step_count(self, env):
        """Test step() increments state.step_count by 1 each call."""
        env.reset()
        env._execute_action = MagicMock()  # Prevent xdotool subprocess
        env.step(StarCraftAction(action_type="noop"))
        assert env.state.step_count == 1
        env.step(StarCraftAction(action_type="noop"))
        assert env.state.step_count == 2

    def test_noop_action_does_not_crash(self, env):
        """Test that noop action passes through _execute_action without error."""
        env.reset()
        # _execute_action with noop should return without calling subprocess
        env._execute_action(StarCraftAction(action_type="noop"))  # should not raise

    def test_step_without_reset_triggers_reset(self, env):
        """Test step() calls reset() when app is not running."""
        assert env._state.app_running is False
        env.step(StarCraftAction(action_type="noop"))
        # reset was called (via env.reset() inside step)
        env._start_game.assert_called_once()

    def test_state_property_returns_starcraft_state(self, env):
        """Test state property returns a StarCraftState instance."""
        assert isinstance(env.state, StarCraftState)

    def test_consecutive_resets_call_cleanup(self, env):
        """Test that each reset() calls _cleanup to kill prior game process."""
        env.reset()
        env.reset()
        assert env._cleanup.call_count == 2

    @pytest.mark.skip(
        reason="Requires Wine, Xvfb, and StarCraft.exe — only runs inside Docker container"
    )
    def test_full_game_launch(self):
        """Integration: start the real game and verify app_running=True.

        Skipped: needs Wine + Xvfb + game binary at /apps/Starcraft/StarCraft.exe.
        """
        env = StarCraftEnvironment()
        env.reset()
        assert env.state.app_running is True

    @pytest.mark.skip(
        reason="Requires xdotool installed and an active X11 display (:0)"
    )
    def test_key_action_via_xdotool(self):
        """Integration: send a real key press via xdotool.

        Skipped: needs xdotool and DISPLAY=:0 available.
        """
        env = StarCraftEnvironment()
        env._start_game = MagicMock()
        env._cleanup = MagicMock()
        env.reset()
        env.step(StarCraftAction(action_type="key", key="Return"))


class TestStarCraftClient:
    """Test StarCraftEnv client methods without making real network connections."""

    @pytest.fixture
    def client(self):
        """Instantiate the client pointed at a dummy URL (no connection made)."""
        return StarCraftEnv(base_url="http://localhost:9999")

    # --- _step_payload tests ---

    def test_step_payload_key_action(self, client):
        """Test _step_payload for key action includes action_type and key."""
        action = StarCraftAction(action_type="key", key="Return")
        payload = client._step_payload(action)
        assert payload == {"action_type": "key", "key": "Return"}

    def test_step_payload_key_action_excludes_mouse_fields(self, client):
        """Test _step_payload for key action does not include mouse coordinates."""
        action = StarCraftAction(action_type="key", key="Escape")
        payload = client._step_payload(action)
        assert "x" not in payload
        assert "y" not in payload
        assert "button" not in payload
        assert "mouse_state" not in payload

    def test_step_payload_mouse_action(self, client):
        """Test _step_payload for mouse action includes all mouse fields."""
        action = StarCraftAction(
            action_type="mouse", x=0.5, y=0.25, button="left", mouse_state="click"
        )
        payload = client._step_payload(action)
        assert payload == {
            "action_type": "mouse",
            "x": 0.5,
            "y": 0.25,
            "button": "left",
            "mouse_state": "click",
        }

    def test_step_payload_noop_action(self, client):
        """Test _step_payload for noop contains only action_type."""
        action = StarCraftAction(action_type="noop")
        payload = client._step_payload(action)
        assert payload == {"action_type": "noop"}

    def test_step_payload_mouse_right_button(self, client):
        """Test _step_payload correctly passes right button for mouse action."""
        action = StarCraftAction(
            action_type="mouse", x=0.8, y=0.9, button="right", mouse_state="click"
        )
        payload = client._step_payload(action)
        assert payload["button"] == "right"

    # --- _parse_result tests ---

    def test_parse_result_builds_step_result(self, client):
        """Test _parse_result constructs a StepResult with correct reward and done."""
        raw = {
            "observation": {
                "screen_image": "data:image/png;base64,abc",
                "screen_shape": [480, 640, 3],
                "game_pixel_similarity": 0.85,
            },
            "reward": 1.0,
            "done": True,
        }
        result = client._parse_result(raw)
        assert isinstance(result, StepResult)
        assert isinstance(result.observation, StarCraftObservation)
        assert result.reward == 1.0
        assert result.done is True

    def test_parse_result_observation_fields(self, client):
        """Test _parse_result populates observation fields correctly."""
        raw = {
            "observation": {
                "screen_image": "data:image/png;base64,xyz",
                "screen_shape": [480, 640, 3],
                "game_pixel_similarity": 0.42,
            },
            "reward": 0.0,
            "done": False,
        }
        result = client._parse_result(raw)
        obs = result.observation
        assert obs.screen_image == "data:image/png;base64,xyz"
        assert obs.screen_shape == [480, 640, 3]
        assert obs.game_pixel_similarity == 0.42

    def test_parse_result_defaults_on_empty_payload(self, client):
        """Test _parse_result uses sensible defaults when payload is empty."""
        result = client._parse_result({})
        assert result.reward == 0.0
        assert result.done is False
        obs = result.observation
        assert obs.screen_image is None
        assert obs.screen_shape == [480, 640, 3]
        assert obs.game_pixel_similarity == 0.0

    def test_parse_result_defaults_on_empty_observation(self, client):
        """Test _parse_result handles missing 'observation' key gracefully."""
        raw = {"reward": -1.0, "done": True}
        result = client._parse_result(raw)
        assert result.reward == -1.0
        assert result.done is True
        assert result.observation.screen_image is None

    # --- _parse_state tests ---

    def test_parse_state_builds_starcraft_state(self, client):
        """Test _parse_state constructs StarCraftState from payload dict."""
        raw = {
            "step_count": 7,
            "episode_id": "ep-abc",
            "app_running": True,
        }
        state = client._parse_state(raw)
        assert isinstance(state, StarCraftState)
        assert state.step_count == 7
        assert state.episode_id == "ep-abc"
        assert state.app_running is True

    def test_parse_state_defaults_on_empty_payload(self, client):
        """Test _parse_state uses defaults when payload is empty."""
        state = client._parse_state({})
        assert state.step_count == 0
        assert state.episode_id == ""
        assert state.app_running is False

    def test_parse_state_app_not_running(self, client):
        """Test _parse_state correctly reflects app_running=False."""
        raw = {"step_count": 0, "episode_id": "", "app_running": False}
        state = client._parse_state(raw)
        assert state.app_running is False

# StarCraft: Brood War Environment

A Dockerized environment for running StarCraft: Brood War with OpenEnv.

## Overview

This environment runs StarCraft inside a Wine container with a virtual X server (Xvfb).
It exposes an HTTP API to send inputs (keyboard/mouse) and receive screen captures.

## Requirements

1. **StarCraft Game Files**: You must have a legal copy of StarCraft installed functionality.
   - Expected path on host: `winvm/apps/Starcraft` relative to the project root (or wherever you mount it).
   - The folder must contain `StarCraft.exe` and `fast.reg` / `StarCraft.mpq` etc.

2. **Docker**: To build and run the container.

## Setup

### Build Docker Image

```bash
cd OpenEnv
docker build -t openenv-starcraft -f envs/starcraft_env/server/Dockerfile .
```

### Run Container

Mount your StarCraft apps folder to `/apps` in the container.

```bash
docker run -d \
  --name openenv-starcraft \
  -p 8000:8000 \
  -v /path/to/your/Starcraft:/apps/Starcraft:ro \
  openenv-starcraft
```

## Usage

### Python Client

```python
from envs.starcraft_env.client import StarCraftEnv, StarCraftAction

# Connect
env = StarCraftEnv(base_url="http://localhost:8000")
obs = env.reset()

# Act
action = StarCraftAction(action_type="key", key="s") # Start Single Player
obs = env.step(action)

# Observe
print(obs.observation.screen_image) # Base64 PNG
```

### Viewer

Open `http://localhost:8000/viewer` (if supported by base OpenEnv server) or inspect the stream.

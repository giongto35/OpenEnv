#!/bin/bash
set -e

# Export environment variables
export DISPLAY=":0"
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app/src:/app"

echo "Starting Xvfb..."
Xvfb :0 -screen 0 640x480x24 > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 2

echo "Starting Fluxbox..."
fluxbox > /tmp/fluxbox.log 2>&1 &
steps=0
while ! xdpyinfo -display :0 >/dev/null 2>&1; do
  sleep 1
  steps=$((steps+1))
  if [ $steps -ge 10 ]; then
    break
  fi
done
echo "X11 ready."

echo "Starting Uvicorn..."
exec uvicorn envs.starcraft_env.server.app:app --host 0.0.0.0 --port 8000

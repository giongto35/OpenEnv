# StarCraft Environment Docker Image
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    software-properties-common \
    gpg-agent \
    supervisor \
    xvfb \
    cabextract \
    aptitude \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    netcat-openbsd \
    pulseaudio \
    libpulse0 \
    alsa-utils \
    fluxbox \
    x11-utils \
    xdotool \
    x11-apps \
    scrot \
    imagemagick \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Wine
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    wine \
    wine32 \
    wine64 \
    libwine \
    libpulse0:i386 && \
    rm -rf /var/lib/apt/lists/*

# Install winetricks
RUN wget -nv -O /usr/bin/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
    && chmod +x /usr/bin/winetricks

# Silence Wine debug messages
ENV WINEDEBUG=fixme-all

# Install common Wine dependencies
RUN winetricks d3dx9_43 || true
RUN winetricks -q sound=pulse || true

# Setup directories
RUN mkdir -p /app /apps /app/logs
WORKDIR /app

# Install Python dependencies
RUN pip3 install --no-cache-dir fastapi uvicorn numpy pillow mss gradio python-multipart fastmcp opencv-python

# Copy OpenEnv core
COPY src/openenv/core/ /app/src/openenv/core/

# Copy Environment Code
COPY envs/starcraft_env/ /app/envs/starcraft_env/

# Copy helper scripts from resources if any (assuming none for now, using inline supervisor config)
# Create supervisor config
RUN echo "[supervisord]\n\
    nodaemon=true\n\
    \n\
    [program:xvfb]\n\
    command=/usr/bin/Xvfb :0 -screen 0 640x480x24\n\
    autorestart=true\n\
    priority=100\n\
    \n\
    [program:fluxbox]\n\
    command=/usr/bin/fluxbox\n\
    environment=DISPLAY=\":0\"\n\
    autorestart=true\n\
    priority=200\n\
    \n\
    [program:app]\n\
    command=uvicorn envs.starcraft_env.server.app:app --host 0.0.0.0 --port 8000\n\
    environment=DISPLAY=\":0\",PYTHONPATH=\"/app/src:/app\"\n\
    autorestart=true\n\
    priority=300\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n\
    " > /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 8000

COPY envs/starcraft_env/server/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]

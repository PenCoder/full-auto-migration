# Use Ubuntu 20.04 for best cross-distro compatibility
FROM python:3.11-slim AS builder

# Prevent timezone prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install System Dependencies (Python + Tkinter)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# 2. Set the working directory
WORKDIR /src

# 3. Install Python Dependencies
# We copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt pyinstaller

# 4. Run PyInstaller to create a standalone executable
COPY . .


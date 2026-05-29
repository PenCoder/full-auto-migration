# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — PyInstaller + AppImage packaging
# Produces a single double-clickable MigrationWizard-x86_64.AppImage.
# Run via:  bash build_linux.sh
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# System libraries required by PySide6 at build time + wget for appimagetool.
RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils \
        file \
        wget \
        libgl1 \
        libglib2.0-0 \
        libegl1 \
        libdbus-1-3 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Download appimagetool (APPIMAGE_EXTRACT_AND_RUN=1 bypasses FUSE inside Docker).
RUN wget -q \
    https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage \
    -O /usr/local/bin/appimagetool \
    && chmod +x /usr/local/bin/appimagetool

WORKDIR /build

# Install Python dependencies (platform guard in requirements.txt skips winapps).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pyinstaller==6.17.0

# Copy source.
COPY . .

# ── Step 1: PyInstaller → /build/dist/MigrationWizard/ ───────────────────────
RUN pyinstaller \
        --noconfirm \
        --onefile \
        --windowed \
        --name "MigrationWizard" \
        --add-data "configs:configs" \
        --add-data "src/qt_ui/theme.qss:src/qt_ui" \
        --add-data "src/qt_ui/assets:src/qt_ui/assets" \
        --hidden-import "PySide6.QtSvg" \
        --hidden-import "PySide6.QtPrintSupport" \
        app.py

# ── Step 2: Assemble AppDir ───────────────────────────────────────────────────
RUN mkdir -p /build/MigrationWizard.AppDir/usr/bin \
    && cp /build/dist/MigrationWizard     /build/MigrationWizard.AppDir/usr/bin/MigrationWizard \
    && chmod +x /build/MigrationWizard.AppDir/usr/bin/MigrationWizard \
    && cp /build/packaging/AppRun         /build/MigrationWizard.AppDir/AppRun \
    && chmod +x /build/MigrationWizard.AppDir/AppRun \
    && cp /build/packaging/MigrationWizard.desktop \
          /build/MigrationWizard.AppDir/MigrationWizard.desktop \
    && cp /build/src/qt_ui/assets/app.png \
          /build/MigrationWizard.AppDir/MigrationWizard.png

# ── Step 3: Package → MigrationWizard-x86_64.AppImage ────────────────────────
RUN APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 \
    /usr/local/bin/appimagetool \
    /build/MigrationWizard.AppDir \
    /build/dist/MigrationWizard-x86_64.AppImage

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime image — run the app inside a container with X11 forwarding.
# Not required for normal use; useful for testing the AppImage on a headless host.
# Usage: docker compose up runtime   (with DISPLAY forwarded)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libegl1 libdbus-1-3 \
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 \
        libxcb-xinerama0 libxkbcommon-x11-0 fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/dist/MigrationWizard-x86_64.AppImage /app/
COPY --from=builder /build/configs /app/configs

VOLUME ["/data"]
ENV DISPLAY=:0
CMD ["/bin/bash", "-c", \
     "APPIMAGE_EXTRACT_AND_RUN=1 /app/MigrationWizard-x86_64.AppImage"]

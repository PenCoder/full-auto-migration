# Downloads

Pre-built binaries are attached to [GitHub Releases](https://github.com/PenCoder/full-auto-migration/releases) — no Python or dependencies required.

## Windows

[Download migrate.exe](https://github.com/PenCoder/full-auto-migration/releases/latest/download/migrate.exe){ .md-button .md-button--primary }

Double-click `migrate.exe` and follow the 7-step wizard. This build embeds a pre-built Linux `restore` binary internally, so every migration bundle it creates is fully self-contained — no separate Linux download needed.

## Linux Mint

The `restore` binary is copied into your migration bundle automatically by `migrate.exe` — you don't need to download it separately. Just copy the bundle to your Linux Mint machine and double-click the binary inside it. If nothing happens on double-click: right-click the file → Properties → Permissions → tick "Allow executing file as program".

A standalone copy is also [available for direct download](https://github.com/PenCoder/full-auto-migration/releases/latest/download/restore){ .md-button } if you want to run the Linux side without going through the Windows bundle flow.

!!! note "Linux binary availability"
    The `restore` binary must be built directly on a Linux Mint machine — PyInstaller doesn't cross-compile. It may not always be attached to every release as a standalone asset; check the [release notes](https://github.com/PenCoder/full-auto-migration/releases). If it's missing, you can build it yourself — see "Run from source" below.

## Run from source instead

```bash
git clone https://github.com/PenCoder/full-auto-migration.git
cd full-auto-migration
pip install -r requirements.txt
python app.py
```

See the [README](https://github.com/PenCoder/full-auto-migration#readme) for the full CLI reference and build instructions.

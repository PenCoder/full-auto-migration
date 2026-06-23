# Downloads

Pre-built binaries are attached to [GitHub Releases](https://github.com/PenCoder/full-auto-migration/releases) — no Python or dependencies required.

## Windows

[Download migrate.exe](https://github.com/PenCoder/full-auto-migration/releases/latest/download/migrate.exe){ .md-button .md-button--primary }

Double-click `migrate.exe` and follow the 7-step wizard. If you already have a `restore` binary (see below) sitting next to it in `assets/linux_build/`, it gets baked into the `.exe` automatically as a single standalone file.

## Linux Mint

[Download restore](https://github.com/PenCoder/full-auto-migration/releases/latest/download/restore){ .md-button }

Copy the binary from the migration bundle (or download it directly) to your Linux Mint machine and double-click it. If nothing happens on double-click: right-click the file → Properties → Permissions → tick "Allow executing file as program".

!!! note "Linux binary availability"
    The `restore` binary must be built directly on a Linux Mint machine — PyInstaller doesn't cross-compile. It may not always be attached to every release; check the [release notes](https://github.com/PenCoder/full-auto-migration/releases) for which assets are included. If it's missing, you can build it yourself — see "Run from source" below.

## Run from source instead

```bash
git clone https://github.com/PenCoder/full-auto-migration.git
cd full-auto-migration
pip install -r requirements.txt
python app.py
```

See the [README](https://github.com/PenCoder/full-auto-migration#readme) for the full CLI reference and build instructions.

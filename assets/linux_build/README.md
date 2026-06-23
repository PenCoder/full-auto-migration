# Pre-built Linux binary

This folder is where the Windows-side backup step looks for a pre-built
Linux executable of this same tool. If `restore` exists here, it
gets copied into every migration bundle, so the bundle.zip carried over to
Linux is fully self-contained: unzip, run the binary, restore.

## How to build it

PyInstaller does not cross-compile — you must run it **on Linux** (e.g. the
Linux Mint VM):

```bash
cd /path/to/project   # the same source tree, copied or shared onto the VM
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller MigrationWizard_linux.spec
```

This produces `dist/restore`. Copy that single file back into this
folder (`assets/linux_build/restore`) on the Windows side, and make
sure it's executable (`chmod +x restore` before zipping, or the
bundling step sets the bit — see `migration_service.py`).

## Notes

- Rebuild and replace this file whenever the app's Python source changes —
  it is not kept in sync automatically.
- The binary is intentionally not committed to git (see `.gitignore`); it's
  a local build artifact, large (~100-300MB with PySide6), and platform/arch
  specific.
- If this file is absent, bundle creation just skips embedding a binary —
  the bundle still works for restore via the existing Python-source path.

# User Migration Guide: Windows 11 to Linux Mint

This guide walks you through using the **Sovereignty Migration Platform** to safely move your files, settings, and applications from Windows 11 to Linux Mint. No technical expertise is required.

---

## Before You Start

**What you will need:**
- A USB flash drive (16 GB or larger)
- About 1–2 hours of time
- This migration tool installed on your Windows 11 machine

**What the tool will do for you:**
1. Scan your Windows system to find your installed applications and important files
2. Suggest equivalent Linux applications for each Windows app you use
3. Pack your personal files into a secure backup bundle
4. Guide you through installing Linux Mint
5. Restore your files and help you install your new Linux apps

**What this tool does NOT move:**
- Windows programs themselves — it installs the Linux versions instead
- Passwords or browser history
- Windows system settings

---

## Step 1: Choose Your Migration Mode

When you open the application, you will be asked to choose a **mode**. Each mode controls how much the tool does automatically for you.

| Mode | Best for | What it does |
|---|---|---|
| **Guided** | First-time users | Scans your system, suggests apps, packs your files — minimal decisions required |
| **Balanced** | Most users | Everything in Guided, plus file type analysis and usage-based prioritisation |
| **Expert** | Power users | Everything in Balanced, plus live online package verification and full manual overrides |

**Recommendation:** Start with **Balanced** if you are unsure.

---

## Step 2: Scan Your Windows System

Click **Run Scan** on the Scan page. The tool will:

- Detect all installed applications (e.g. Microsoft Office, Google Chrome, VLC)
- Scan your Documents, Desktop, and other configured folders
- Detect your desktop theme and wallpaper

This takes 1–3 minutes. You will see a summary when it finishes.

> **Privacy note:** Nothing leaves your machine during the scan. All data stays local.

---

## Step 3: Review Your Application Mapping

The tool will show you a table of your Windows applications and the suggested Linux equivalents.

Example mappings:

| Your Windows app | Suggested Linux app | Confidence |
|---|---|---|
| Microsoft Word | LibreOffice Writer | High |
| Google Chrome | Google Chrome (Linux) | High |
| Spotify | Spotify (Linux client) | High |
| Notepad++ | NotepadQQ | Medium |

**What the confidence levels mean:**
- **High** — Direct equivalent available in Linux Mint's software repositories
- **Medium** — A good alternative is available; minor workflow differences expected
- **Low** — No close equivalent found; manual research recommended

You can override any mapping by clicking the app row and selecting a different Linux package.

---

## Step 4: Select Your Files

On the **Data Selection** page, choose which files to migrate:

- **All files** — Migrates everything in your configured folders (Documents, Desktop, etc.)
- **Selected types** — Choose specific file types (e.g. only PDFs and Word documents)
- **Manual** — You will handle your files yourself; the tool skips this step

The tool automatically marks frequently-used and important files (source code, documents, config files) as high priority.

---

## Step 5: Create Your Backup Bundle

Click **Create Backup Bundle**. The tool will:

1. Copy all your selected files into a compressed archive (`backup.zip`)
2. Compute a checksum for every file so the restore can verify nothing was corrupted
3. Save a `manifest.json` listing all files, sizes, and checksums

When finished, **copy the entire backup folder to your USB drive** or an external hard disk.

> Keep your backup safe. You will need it after Linux Mint is installed.

---

## Step 6: Install Linux Mint

1. Download the Linux Mint ISO from [linuxmint.com](https://linuxmint.com) (Cinnamon edition recommended)
2. Use **Rufus** (Windows) to write the ISO to your USB drive
3. Reboot your computer from the USB drive
4. Follow the Linux Mint installer steps
5. Once Linux Mint is installed and running, copy your backup folder from the USB drive to your home directory

---

## Step 7: Restore Your Files (on Linux Mint)

Open the migration tool on Linux Mint and switch to **Linux Restore** mode (the tool detects the OS automatically).

Click **Restore Files**. The tool will:

1. Read your backup bundle and manifest
2. Copy all files to `~/Restored_Migration/`
3. Verify each file against its checksum to confirm nothing was corrupted
4. Generate a restore report

---

## Step 8: Review the Validation Report

After the restore, a **Validation Report** is generated showing:

- How many files were successfully restored
- Any files that failed the checksum check (hash mismatch)
- Any files that are missing from the backup
- A **Sovereignty Score** (0–100%) summarising the overall migration quality

A score above 90% means an excellent migration. If any files failed, the report lists them individually so you can re-copy them manually.

---

## Step 9: Install Your Linux Applications

Use the application mapping from Step 3 as your shopping list. On Linux Mint, open the **Software Manager** and install each recommended application.

For applications marked as `apt` (most of them):
```
sudo apt install firefox libreoffice vlc thunderbird
```

For applications marked as `external`, follow the link in the recommendation notes to download from the official website (e.g. Spotify, Discord).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Scan finds no applications | Run as Administrator; check that the registry scan completed |
| Backup creation fails | Ensure you have write access to the backup folder and enough disk space |
| A file is listed as missing after restore | Manually copy it from your USB backup to `~/Restored_Migration/` |
| Application not in the mapping list | Search the Linux Mint Software Manager or visit [repology.org](https://repology.org) |
| Sovereignty Score is below 75% | Review the failed and missing file lists in the validation report |

---

## Frequently Asked Questions

**Will my files be safe?**
Yes. The tool only reads your files during the scan and copies them during backup. It never modifies originals. Your Windows installation remains untouched until you choose to replace it.

**Can I use the tool without online lookups?**
Yes. Guided and Balanced mode only ever use local, offline analysis. The optional online package verification (via Repology) only runs in Expert mode — it is never used otherwise, regardless of mode.

**What if I do not want to migrate all my files?**
Use **Selected types** mode in Step 4 to choose only the file types you care about (e.g. documents and photos only).

**Can I undo the migration?**
The tool never modifies your Windows system. Your original files are always available on the backup drive. You can reinstall Windows at any time.

---

## Privacy Summary

| Data | What happens |
|---|---|
| Your file contents | Stored only on your local machine and backup drive — never transmitted |
| Application names | Only the software name/version is sent to Repology (optional, for availability checks) |
| Your file paths | Redacted in all external communications |
| Your personal data | Never leaves your machine |

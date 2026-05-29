# User Manual
## Migration Wizard — Moving from Windows 11 to Linux Mint

**Version 1.0 — May 2026**

---

> **What this tool does**
>
> It helps you move your personal files, programs list, and desktop settings from your Windows computer to a new Linux Mint computer — automatically, step by step, without needing any technical knowledge.

---

## Before You Start

### What you will need

| Item | Why you need it |
|---|---|
| A USB stick — at least 32 GB | To carry your files from Windows to Linux |
| Your Windows computer | To run the first part of the tool |
| Your new Linux Mint computer | To run the second part of the tool |
| An internet connection | Only on the Linux computer, to install apps |

### What this tool moves for you

- Your personal files — Documents, Pictures, Music, Videos, Desktop, Downloads
- A list of your Windows programs, matched to their Linux equivalents
- Your desktop wallpaper
- Your light or dark mode preference

### What this tool does NOT move

- Windows programs themselves — it installs the Linux versions instead
- Passwords or browser history
- Windows system settings

---

## Part 1 — On Your Windows Computer

### Step 1 — Get the tool

Copy the file `MigrationWizard.exe` to your Windows computer.

You can get it from your USB stick or download it from the project page.

---

### Step 2 — Run the tool

Double-click `MigrationWizard.exe`.

> **Note:** Windows may show a security warning the first time. Click **"More info"** then **"Run anyway"** to continue.

The wizard opens. You will see a welcome screen.

---

### Step 3 — Choose your mode

The tool asks you to choose how much control you want.

| Mode | Best for | What it does |
|---|---|---|
| **Guided** | Most people | Makes all decisions for you automatically |
| **Balanced** | Comfortable with computers | You choose which types of files to move |
| **Expert** | Advanced users | Full control over every setting |

> **Recommendation:** Choose **Guided** if you are not sure.

Click **Next** to continue.

---

### Step 4 — Scanning your computer

The tool scans your computer automatically. You do not need to click anything.

It is looking for:
- Your installed programs
- Your hardware (graphics card, processor, etc.)
- Your desktop settings (wallpaper, theme)

This takes about **30 to 60 seconds**.

When it finishes you will see a list of your programs and their Linux alternatives.

> **Example:** Microsoft Word → LibreOffice Writer · VLC → VLC · Chrome → Chromium

Click **Next** to continue.

---

### Step 5 — Settings migration

The tool shows you what desktop settings it found — your wallpaper and colour theme.

In Guided mode, everything is saved automatically.

Click **Next** to continue.

---

### Step 6 — Choose your files

The tool asks which files you want to move.

In Guided mode, all your personal files are selected automatically.

In Balanced or Expert mode, you can choose specific file types — for example, only documents and photos.

Click **Next** to continue.

---

### Step 7 — Review your migration plan

You will see a summary of:
- Which programs will be installed on Linux
- Which files will be moved

Check the lists look correct. If something is missing, do not worry — you can always copy more files manually later.

Click **Next** to continue.

---

### Step 8 — Creating your migration bundle

The tool now packs everything up automatically. You do not need to click anything.

It creates a folder called `data/restore/` inside the tool's folder. This folder contains:
- All your selected files (compressed into a single archive)
- Your list of programs to install
- Your desktop settings and wallpaper

This takes **2 to 10 minutes** depending on how many files you have.

When it finishes you will see a message saying your bundle is ready.

---

### Step 9 — Copy the bundle to your USB stick

Open **File Explorer** on Windows.

Navigate to the folder where the tool is installed. You will see a folder called `data`.

Copy the **entire `data` folder** to your USB stick.

Also copy the **`MigrationWizard.AppImage`** file (for Linux) to the USB stick.

Your USB stick should look like this when you are done:

```
USB stick
├── MigrationWizard.AppImage
└── data/
    └── restore/
        ├── backup.zip
        ├── manifest.json
        ├── apps_to_install.json
        ├── settings_inventory.json
        └── settings_assets/
            └── wallpaper.jpg
```

> **Important:** Do not rename or move any of these files. The tool needs them exactly where they are.

---

## Part 2 — On Your Linux Mint Computer

### Step 10 — Plug in the USB stick

Plug your USB stick into your Linux Mint computer.

Linux Mint will detect it automatically. You will see it appear in the Files app on the left side.

---

### Step 11 — Run the tool

Open the Files app and navigate to your USB stick.

Find the file called `MigrationWizard.AppImage`.

Double-click it to run it.

> **Note:** If nothing happens when you double-click, right-click the file and look for **"Properties"**. Go to the **Permissions** tab and tick the box that says **"Allow executing file as program"**. Then try double-clicking again.

---

### Step 12 — Restore your files

The tool opens on the Restore page.

Click **Browse** and navigate to the `data/restore/` folder on your USB stick.

Select the `restore` folder and click **OK**.

The tool starts restoring your files automatically. You do not need to click anything.

It will:
1. Copy your files to the correct folders — Documents to Documents, Pictures to Pictures, and so on
2. Apply your wallpaper
3. Set your light or dark mode preference
4. Install your programs using the software manager

> **Note:** Installing programs requires an internet connection. A password prompt may appear — this is normal. Enter your Linux Mint password to allow the installation.

This takes **5 to 20 minutes** depending on how many files and programs you have.

---

### Step 13 — Verification

After the restore finishes, the tool automatically checks that all your files arrived safely.

It compares each file against the original using a digital fingerprint (SHA-256 checksum).

You will see a **Migration Score** — a percentage showing how much of your data moved successfully.

| Score | What it means |
|---|---|
| 90% or above | Excellent — almost everything moved perfectly |
| 70% to 89% | Good — a few files may need attention |
| Below 70% | Some files had problems — check the report |

---

### Step 14 — Your migration report

The tool generates a final report automatically.

Click **Open Report** to open it in your browser.

The report shows:
- How many files were moved
- Which programs were installed
- Your final Migration Score
- Any files that could not be moved

Save or print this report for your records.

---

## What happened to your settings?

After the restore, a file called **`settings_migration_guidance.md`** appears in your home folder.

Open it with a text editor to see:
- Which settings were applied automatically
- Which settings need to be adjusted manually — for example, accent colour or keyboard shortcuts

---

## Frequently Asked Questions

**My files are not in the right place on Linux.**
The tool puts files in the standard Linux folders — Documents go to `~/Documents`, Pictures to `~/Pictures`, and so on. Open the Files app and look there first.

**A program is missing after the restore.**
Some Windows programs do not have a direct Linux equivalent. Open the Software Manager in Linux Mint and search for an alternative manually.

**The wallpaper did not change.**
Go to System Settings → Background and select the wallpaper file manually. It was saved to your `Pictures` folder during the restore.

**The tool says "Bundle not found".**
Make sure you selected the `restore` folder, not the `data` folder. The correct path ends in `data/restore/`.

**I see a password prompt during app installation.**
This is normal. The tool needs your Linux Mint password to install programs. Type it and press Enter.

**Can I run the restore more than once?**
Yes. The tool skips files that are already present and identical — it will not overwrite newer versions of your files.

**My Migration Score is low.**
Open the report and look at the list of files that could not be moved. Most low scores are caused by very large files (over 500 MB) or files that were locked by another program during backup. Copy those files manually from the USB stick.

**I do not have an internet connection on Linux.**
The file restore and settings will still work without internet. Only the program installation step needs a connection. You can install programs manually later using the Software Manager.

---

## Need help?

The project is open-source and available at:

**https://github.com/PenCoder/full-auto-migration**

---

*Migration Wizard User Manual — Version 1.0 — May 2026*
*Author: Japhet Kofi Appau Arthur*

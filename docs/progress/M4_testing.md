# Milestone M4 — Testing & Validation  
**Time Frame:** Weeks 7–8  
**Status:** In Progress (Restore + Validation integrated)

---

## 1. Objective
Milestone M4 verifies the reliability of the migration framework through controlled tests in Linux environments.  
The primary goals are:

- confirm successful restoration of files from the migration bundle
- confirm automated application installation without terminal interaction
- verify integrity using cryptographic hashes
- record validation outputs for reporting and evaluation

---

## 2. Test Environment Setup

### 2.1 Virtual Environment (Recommended for repeatability)
- Linux Mint VM (VirtualBox)
- Fresh installation (clean state)
- Migration bundle provided via shared folder or mounted USB image

### 2.2 Physical Environment (Planned)
- At least one physical machine for validation
- Focus: firmware/driver edge cases, external disk handling, performance

---

## 3. Test Artifacts

### 3.1 Migration Bundle Structure
Expected bundle content:

- `manifest.json` — file list + SHA-256 per file
- `backup.zip` — archived file payload
- `apps_to_install.json` — Linux packages to install (apt-based)

### 3.2 Restore Outputs (Linux)
- Restored files copied into user home directory (preserving relative paths)
- Application installation executed via `pkexec apt install -y ...`
- Validation results persisted to: `data/validation/validation_results.json`

---

## 4. Test Procedure (VM)

1. Boot Linux Mint VM (fresh install)
2. Launch Migration Wizard (Linux runtime flow)
3. Open Restore page → select migration bundle directory
4. Start Restore:
   - extraction of `backup.zip`
   - file restore to `/home/<user>/...`
   - hash verification against `manifest.json`
   - application installation using `pkexec` GUI authentication
5. Run Validation page checks:
   - home directory
   - network connectivity
   - selected app presence (e.g., LibreOffice/VLC)
6. Confirm JSON output created:
   - `data/validation/validation_results.json`

---

## 5. Metrics to Record (for evaluation)

- Restore duration (start → completed)
- Total files restored (from manifest)
- Hash verification pass rate (expected: 100%)
- App installation success (installed packages present in PATH)
- Validation summary (passed/failed counts)

---

## 6. Known Issues Log (to maintain)
Track:
- pkexec authentication failures / policykit errors
- missing packages (repository availability)
- permission problems on restore destination
- hash mismatch cases (file corruption or path mismatch)

---

## 7. Current Status (Tangible Progress)
- Restore wizard UI integrated (Linux flow)
- Progress percentage shown during restore/verify
- Automated app installation implemented via pkexec
- Validation results exported to JSON for reporting

---

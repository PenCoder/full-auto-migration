# Discovery & Analysis Report  
### Milestone M2 — Semi-Automated Migration from Windows 11 to Linux Mint  
### Julius-Maximilians-Universität Würzburg — MSc Informatik Project

---

## 1. Introduction

This report summarizes all analytical findings generated in Milestone M2 of the project **“Semi-Automated Migration from Windows 11 to Linux Mint using a Python-Based Migration Framework.”**  
The objective of M2 is to collect and analyze empirical data from the Windows source system to support the design of the migration framework implemented in later milestones.

This report consolidates:

- Hardware inventory results  
- Software inventory results  
- Hardware compatibility matrix  
- Software mapping table  
- Backup manifest analysis  
- Data migration planning  

The findings in this report form the foundation for the design of the automated migration workflow (Milestone M3) and inform the evaluation methodology (Milestones M4–M6).

---

## 2. Hardware Inventory Analysis

### 2.1 Data Collection Method
Hardware information was collected using the Python module:

```
src/inventory/hardware.py
```

The module executes a series of Windows PowerShell commands to gather structured device information, including:

- CPU  
- RAM modules  
- GPU  
- Physical and logical disks  
- Network adapters  
- BIOS, firmware type, and TPM information  

All results were saved to:

```
data/inventory/hardware_inventory.json
```

### 2.2 Hardware Summary
The inventory revealed the key hardware components of the system, including:

- **Processor:** Detailed core count, logical processors, vendor, and clock speed  
- **Graphics Adapter(s):** Adapter name, vendor, driver details, and VRAM  
- **Memory Modules:** Number of sticks, capacities, speeds  
- **Disk Devices:** NVMe/SATA detection, drive models, interface types  
- **Network Adapters:** Wired/wireless interfaces, MAC addresses, vendor  
- **Firmware:** Detection of BIOS/UEFI mode and Secure Boot availability  
- **TPM:** Version and activation state  

### 2.3 Hardware Migration Considerations
- NVMe and SATA drives are fully supported by Linux Mint.  
- Intel/AMD GPUs rely on native open-source drivers.  
- NVIDIA GPUs require proprietary driver installation during or after setup.  
- Wireless network adapters (Realtek/Broadcom) may require firmware installation.  
- UEFI mode is recommended for installation; Secure Boot should be disabled if using NVIDIA drivers.

---

## 3. Hardware Compatibility Matrix

### 3.1 Purpose
The hardware compatibility matrix classifies each detected hardware component according to its expected support level under Linux Mint.

### 3.2 Generation Method
Generated using:

```
src/analysis/hw_matrix.py
```

Output saved at:

```
data/analysis/hardware_matrix.csv
```


### 3.3 Classification Principles
- **GPU:**  
  - NVIDIA → proprietary driver required  
  - Intel/AMD → native kernel support  
- **Network Adapters:**  
  - Intel/Realtek → generally supported  
  - Broadcom → may require proprietary firmware packages  
- **Storage:**  
  - NVMe and SATA devices → fully supported  

### 3.4 Findings
The system’s hardware is broadly Linux-compatible. Only minor post-installation checks may be needed for wireless adapters or proprietary GPU drivers.

---

## 4. Software Inventory Analysis

### 4.1 Data Collection Method
Software inventory was collected using:

```
src/inventory/software.py
```


It enumerates applications installed on the system via Windows Registry paths and outputs results to:

```
data/inventory/software_inventory.json
```


### 4.2 Inventory Findings
The inventory includes:

- Browsers  
- Office and productivity tools  
- Development tools  
- Media applications  
- Communication tools  
- Numerous system-level components (SDKs, runtimes, Visual Studio sub-packages, diagnostic tools)

### 4.3 Observed Distribution of Software
- **User-facing applications:** Chrome, Firefox, Office 365, VS Code, VLC, Zoom, TeamViewer, Anaconda, GitHub Desktop, Postman, etc.  
- **Developer toolchains:** Visual Studio, .NET SDKs, Node.js, Java JDK, Android Studio, JetBrains Toolbox  
- **Low-level components:** Visual C++ Redistributables, .NET runtimes, CUDA-related packages, SQL Server internal packages  
- **Sub-component packages:** Visual Studio Toolchain internal modules, Intellisense files, Click-to-Run dependencies for Office, SQL engine fragments  

These internal components are *not* directly relevant for application-level migration.

---

## 5. Software Mapping Table

### 5.1 Purpose
To identify Linux equivalents for user-relevant Windows applications.

### 5.2 Generation Method
Generated using:

```
src/analysis/software_mapping.py
```

Stored at:

```
data/analysis/software_mapping.csv
```


### 5.3 Filtering Strategy
The mapping table keeps **only user-facing applications**, filtering out:

- SDKs  
- Runtimes  
- Redistributables  
- Windows frameworks  
- Visual Studio internal packages  
- Diagnostic and debugging tools  
- SQL Server internal build dependencies  

### 5.4 Mapping Categories
Each application is assigned:

- `category`  
- `linux_package`  
- `migration_strategy`  
- `notes`

### 5.5 Example Mappings
| Windows Application | Category | Linux Equivalent | Migration Strategy |
|---------------------|----------|------------------|---------------------|
| Google Chrome | Browser | Chrome (Linux) | Install equivalent |
| Microsoft 365 Apps | Office | LibreOffice + Web Office | Use web + local equivalent |
| VLC Media Player | Media | VLC | Install equivalent |
| Visual Studio Code | Development | VS Code (Linux) | Install equivalent |
| Mozilla Firefox | Browser | Firefox | Use preinstalled |

All other applications receive `"Manual evaluation required"`—this is academically correct and intentionally conservative.

---

## 6. Backup Manifest Analysis

### 6.1 Method
The backup manifest is generated using:

```
src/backup/manifest.py
```


It scans directories listed in `backup_paths` and excludes directories listed in `excluded_paths`.

### 6.2 Manifest Contents
Each record includes:

- `source_path`  
- `relative_path`  
- `size_bytes`  
- `sha256`  
- Timestamp  

Stored at:

```
data/backup/manifest.json
```


### 6.3 Backup Strategy Highlights
- SHA-256 checksums enable post-migration verification.  
- Backup excludes internal Windows directories and temporary files.  
- Application-specific data is selectively included.

---

## 7. Data Migration Plan

The plan defines **what**, **how**, and **where** data will be migrated.

### 7.1 Data Included
- User documents (Documents, Pictures, Videos, Desktop, Downloads)  
- Project folders  
- User-level configuration where relevant  

### 7.2 Data Excluded
Excluded because Linux Mint independently provides equivalents:

- Windows runtimes  
- .NET SDKs  
- VC++ Redistributables  
- Visual Studio toolchain fragments  
- SQL Server internal components  
- Temporary / cache directories  

### 7.3 Transfer Method
Recommended:  
**External drive formatted as exFAT** for compatibility with both OSes.

### 7.4 Restoration Strategy
- Restore files to `/home/<username>/…`  
- Reinstall Linux equivalents (VS Code, Chrome, VLC, LibreOffice)  
- Rebuild development environments (conda, Node.js, .NET) on Linux  
- Verify integrity via manifest checksums  

---

## 8. Summary of Findings

- The system’s hardware is fully compatible with Linux Mint, with minor GPU or Wi-Fi firmware considerations.  
- User-facing software is easily mapped to Linux equivalents.  
- The majority of inventory entries are development runtimes and SDKs that **do not require migration**.  
- A clean backup manifest ensures integrity during data transfer.  
- All results from this phase will guide the implementation of the automation framework in Milestone M3.

---

## 9. Next Steps (Transition to M3)

Milestone M3 will focus on implementing the **Semi-Automated Migration Framework**, including:

- Python CLI tooling  
- Backup and restore commands  
- System validation checks  
- Linux USB image integration  
- Error handling and logging  

The empirical data collected in M2 serves as the backbone for the design of M3’s automated components.

---



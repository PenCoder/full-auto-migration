# Milestone M2 — Discovery & Analysis  
**Time Frame:** Weeks 2–3  
**Status:** Completed  

---

## 1. Overview

Milestone M2 focuses on gathering, analysing, and structuring empirical system information from the source Windows environment.  
This stage produces the core dataset required for automating migration steps in later milestones.  
The outputs of M2 directly feed into hardware compatibility assessment, software replacement planning, and the definition of the data migration strategy.

---

## 2. Objectives

- Implement a full hardware inventory module using Python and Windows APIs.  
- Implement a software inventory module by querying the Windows Registry.  
- Generate a hardware compatibility matrix for Linux Mint (driver support, kernel compatibility, migration risk).  
- Generate a software mapping table linking Windows applications to Linux Mint alternatives.  
- Draft an initial data migration plan based on inventory results.  
- Produce the discovery and analysis report summarizing insights and system feasibility.

---

## 3. Tasks Completed

### 3.1 Hardware Inventory Module
- Implemented `hardware.py` using WMI/PowerShell to gather:  
  - CPU model & cores  
  - GPU model & driver  
  - RAM modules  
  - Disks & partitions  
  - Network adapters  
  - OS, BIOS, firmware  
- Output saved to: `data/inventory/hardware_inventory.json`

### 3.2 Software Inventory Module
- Implemented `software.py` using Registry queries via Python + PowerShell.  
- Collected installed applications (DisplayName, Publisher, Version).  
- Output saved to: `data/inventory/software_inventory.json`

### 3.3 Hardware Compatibility Matrix
- Python module `hw_matrix.py` created.  
- Cross-referenced hardware components against:  
- Linux Mint driver support  
- Kernel module availability  
- Proprietary vs open-source driver status  
- Output: `data/analysis/hardware_matrix.csv`


### 3.4 Software Mapping Table
- Implemented `software_mapping.py` with structured rules.  
- Automatically maps common apps (Chrome → Chrome, Teams → LibreOffice suite integration, VLC → VLC).  
- Unknown applications flagged as:  

Manual evaluation required

- Output: `data/analysis/software_mapping.csv`


### 3.5 Data Migration Plan (Draft)
Included:  
- Backup paths  
- Excluded paths  
- Restore targets  
- Handling of user directories  
- Recommended migration strategy for non-technical users

### 3.6 Discovery & Analysis Report (Draft)
Summarises:  
- Current system state  
- Software complexity  
- Hardware compatibility risk  
- Expected challenges for full migration  

---

## 4. Evidence of Work

### 4.1 Code Artifacts
- `src/inventory/hardware.py`  
- `src/inventory/software.py`  
- `src/analysis/hw_matrix.py`  
- `src/analysis/software_mapping.py`  
- `src/backup/manifest.py`

### 4.2 Generated Output Files
- `hardware_inventory.json`  
- `software_inventory.json`  
- `hardware_matrix.csv`  
- `software_mapping.csv`  
- `manifest.json`  

### 4.3 Documentation Drafts
- Data migration plan  
- Compatibility notes  
- Partial discovery report  

---

## 5. Diagram — M2 Data Flow

```
      +-------------------------+
      |   Windows 11 System     |
      +-------------------------+
       |                    |
       | Hardware Inventory |
       | Software Inventory |
       v                    v
hardware_inventory.json   software_inventory.json
       |                    |
       v                    v
Hardware Matrix      Software Mapping Table
       \                    /
        \                  /
         \                /
          v              v
     Discovery & Analysis Report
```
---

## 6. Challenges Encountered

- PowerShell inconsistencies while retrieving certain WMI properties.  
- Software inventory containing many system-level components requiring filtering.  
- Determining Linux compatibility for less-common hardware.  
- Ensuring path resolution without hardcoding usernames.  

---

## 7. Next Steps (Leading into M3)

- Integrate all modules into a unified CLI (Typer).  
- Enable configuration-driven path handling.  
- Implement consistent logging and error-handling system.  
- Begin backup manifest generation and restoration planning.  

---

## 8. References

- Linux Mint Hardware Compatibility Guide  
- Linux Mint Driver Manager Documentation  
- Python Standard Library: `pathlib`, `subprocess`, `json`, `hashlib`  
- Microsoft WMI & PowerShell documentation  


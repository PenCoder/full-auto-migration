# Issue 1 — Set Up Test Environments  
**Milestone:** M4 — Testing & Validation  
**Labels:** testing, setup  
**Status:** Completed/Ready to Execute  

---

## 1. Purpose of the Test Environment Setup

This issue prepares all necessary environments for executing controlled and reproducible tests of the semi-automated migration framework.  
Two environment types are required:

1. **Virtualized environments (VirtualBox)**  
2. **Physical machines (real hardware)**  

Testing in these environments ensures that the framework is evaluated under both idealized and real-world system conditions.

---

## 2. Objectives

1. Prepare **consistent Windows 11 test machines** (VM + physical).  
2. Prepare **Linux Mint test environments** (VM + physical target).  
3. Establish a **baseline configuration** for repeatable testing.  
4. Document VM configuration, hardware specs, and system snapshots.  
5. Ensure the same workflow is reproducible across machines.

---

## 3. Environment Requirements

### 3.1 Virtual Environments (VirtualBox)

#### Required VMs:

| VM Name | OS | Purpose |
|--------|----|----------|
| `Win11_Test_VM` | Windows 11 Pro | Test source system for migration |
| `Mint_Test_VM` | Linux Mint 21.3 | Validate restore + post-migration behavior |

#### Virtual Hardware Configuration (Recommended)

| Component | Win11 VM | Mint VM |
|----------|----------|---------|
| CPU | 2 cores | 2 cores |
| RAM | 6–8 GB | 4–6 GB |
| Disk | 80–120 GB | 40–60 GB |
| Graphics | VMSVGA 128 MB | VMSVGA 128 MB |
| Network | NAT + Host-Only | NAT |
| EFI | Enabled | Enabled |

Snapshots:

- `Win11_Clean`  
- `Win11_Baseline` (after installing sample apps)  
- `Mint_Clean`  

All snapshots must be preserved for repeatability.

---

### 3.2 Physical Test Machines

Two physical devices are recommended:

| Device | OS | Purpose |
|--------|----|----------|
| Laptop A | Windows 11 (fresh) | Real hardware inventory + backup test |
| Laptop B | Windows 11 (existing) | Mixed-usage scenario (realistic software list) |

Both must include:

- TPM 2.0  
- Secure Boot ON/OFF states  
- Wi-Fi adapter  
- External USB drive  
- NVMe/SATA disk  

We collect the following from each device:

- Hardware inventory JSON  
- Full specs (CPU, GPU, RAM, firmware, BIOS)  
- Driver versions  
- Disk layout  
- Known manufacturer quirks  

These provide baseline data for comparing VM vs real hardware.

---

## 4. Test Environment Outputs

### 4.1 VM Configuration File

```
docs/technical/environment_config.md
```


Contains:

- VM settings  
- CPU/RAM/disk allocations  
- Snapshots + descriptions  
- OS version + build numbers  

---

### 4.2 System Specification JSON

Generated automatically via:

```bash
python -m src.cli inventory all --yes
```

Output:

```bash
data/inventory/win11_vm_hardware.json
data/inventory/win11_vm_software.json
data/inventory/win11_physical_hardware.json
data/inventory/win11_physical_software.json
```

---

## 5. Environment Setup Diagram

```
                     +-------------------------+
                     |     Test Environments   |
                     +-----------+-------------+
                                 |
        ---------------------------------------------------
        |                                                 |
+-------v--------+                              +---------v--------+
| VirtualBox VM  |                              | Physical Machines |
+----------------+                              +-------------------+
| Win11_Test_VM  |                              | Laptop A (Win11)  |
| Mint_Test_VM   |                              | Laptop B (Win11)  |
+----------------+                              +-------------------+
        |                                                 |
        | Inventory / Backup / Mapping / Analysis         |
        +----------------------+--------------------------+
                               |
                      Ready for M4 Tests
```

## 6. Verification Checklist
VirtualBox Setup

- Windows 11 VM created

- Linux Mint VM created

- Both VMs updated

- VirtualBox Guest Additions installed

- Snapshots created

- Inventory runs successfully

Physical Machines Setup

- Two Windows 11 systems selected

- Inventory commands run

- Hardware differences documented

- Required drivers identified

All items must be checked before proceeding to Issue 2.

---

## 7. Status

**Environment preparation complete.**
Virtual and physical systems are now ready for controlled migration testing in Issue 2.


# Milestone M4 — Testing & Validation  
**Time Frame:** Weeks 7–8  
**Status:** In Progress  

---

## 1. Overview

Milestone M4 evaluates the operational reliability, performance, and correctness of the semi-automated migration framework implemented in M3.  
This milestone tests the end-to-end flow—including inventory, analysis, and backup—and lays the empirical foundation for evaluating automation effectiveness in M5.

Testing is conducted in **two controlled environments**:

1. **Virtualized environments (VirtualBox)**  
2. **Physical machines (real hardware)**  

Both environments allow systematic assessment of:  
- hardware compatibility  
- software mapping consistency  
- backup/restore correctness  
- migration robustness  
- user experience and automation coverage  

---

## 2. Objectives of Milestone M4

1. Prepare standardized virtual and physical test environments.  
2. Run end-to-end migration workflows in a VM.  
3. Run identical workflows on physical systems.  
4. Validate integrity of backup and restore components.  
5. Measure automation success rate and time saved.  
6. Establish a structured Known Issues Log.  

---

## 3. Issues for Milestone M4

### **Issue 1 — Set Up Test Environments**  
**Labels:** `testing`, `setup`  
Prepare all test environments consistently:  
- Create VirtualBox Windows 11 VM snapshot  
- Create VirtualBox Linux Mint VM  
- Identify two physical test laptops/desktops  
- Prepare clean Windows 11 installation or system snapshot  
- Define baseline configuration (ISO version, VM specs, hardware info)  

**Outputs:**  
- environment_config.md  
- VM snapshot files  
- system specifications JSON  

---

### **Issue 2 — Conduct Virtual Migration Test**  
**Labels:** `testing`, `automation`  
Run the complete migration flow inside the VM:  
1. Run hardware inventory  
2. Run software inventory  
3. Generate analysis matrix + mapping  
4. Run backup manifest  
5. (Future) run restore & validate  
6. Capture timing and interaction requirements  

**Metrics Collected:**  
- time to complete each module  
- CPU & RAM usage ranges  
- number of files hashed  
- errors or warnings  
- user interventions needed  

**Outputs:**  
- virtual_test_results.json  
- timing_log.csv  

---

### **Issue 3 — Conduct Physical Machine Test**  
**Labels:** `testing`, `hardware`  
Perform identical workflow on real hardware.  
This validates:  
- actual disk behavior (NVMe/SATA)  
- driver reporting accuracy  
- firmware detection  
- difference between real vs virtual environments  
- robustness of PowerShell commands on physical systems  

**Outputs:**  
- physical_test_results.json  
- hardware_compatibility_notes.md  

---

### **Issue 4 — Evaluate Backup/Restore Integrity**  
**Labels:** `testing`, `data`  
Verify data correctness by comparing:  
- pre-backup SHA-256 hashes  
- post-restore SHA-256 hashes  

Pass criteria:  

For all restored files:
hash_before == hash_after


Test also includes:  
- excluded paths  
- hidden file behavior  
- PATH normalization across OSes  

**Outputs:**  
- integrity_report.csv  

---

### **Issue 5 — Evaluate Automation Success Rate**  
**Labels:** `testing`, `metrics`  
Measure how much of the migration process runs autonomously.  
Key metrics:

| Metric | Description |
|--------|-------------|
| Automation Coverage | % of steps executed without user input |
| Manual Intervention Points | Steps requiring confirmation/data entry |
| Time Saved | VM vs manual comparison |
| Error Rate | Exceptions, PowerShell errors |
| Hardware Divergence | Hardware-specific failures |

**Outputs:**  
- automation_metrics.json  
- comparative_analysis.md  

---

### **Issue 6 — Create Known Issues Log**  
**Labels:** `documentation`, `issues`  
Record all encountered issues:  
- hardware exceptions  
- WMI failures  
- driver mismatches  
- software inconsistencies  
- path-related edge cases  
- unsupported migration conditions  

**Format Example:**

```yaml
- id: ISSUE-001
  category: hardware
  description: "FirmwareType not found on Lenovo ThinkPad L390"
  severity: medium
  workaround: "Fallback to 'Unknown' with log warning"
  status: open
```

Outputs:
```
known_issues.yaml
known_issues_history.md
```

## 4. Testing Workflow Diagram

```

                +--------------------------+
                |    Start M4 Testing      |
                +------------+-------------+
                             |
               +-------------v----------------+
               | 1. Prepare Test Environments |
               +-------------+----------------+
                             |
               +-------------v----------------+
               | 2. Virtual Migration Test    |
               +-------------+----------------+
                             |
               +-------------v----------------+
               | 3. Physical Machine Test     |
               +-------------+----------------+
                             |
               +-------------v----------------+
               | 4. Integrity Validation      |
               +-------------+----------------+
                             |
               +-------------v----------------+
               | 5. Automation Metrics        |
               +-------------+----------------+
                             |
               +-------------v----------------+
               | 6. Known Issues Log          |
               +-------------+----------------+
                             |
                +------------v-------------+
                |     End of M4            |
                +--------------------------+
```

## 5. Outputs Expected for M4

- VM configuration notes
- Physical hardware spec notes
- Integrity validation reports
- Automation metrics dataset
- Known issues documentation
- Comparative VM vs physical analysis

These outputs directly feed Milestone M5 (Evaluation & Optimization).

---

## 6. Status

Milestone M4 is now in progress.
Testing will validate the correctness, robustness, and efficiency of the M3 framework and provide empirical evidence for evaluation in M5.



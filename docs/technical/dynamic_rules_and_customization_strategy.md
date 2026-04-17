# Technical Strategy: Dynamic Rules, Customization, and Multi-Platform Support

## 1. Overview
This document outlines how to evolve from the current hardcoded rule and mapping system to a dynamic, user-customizable, multi-platform architecture. The goal is to eliminate hard-coded decisions and instead generate rules and recommendations at runtime based on detected system state and user preferences.

---

## 2. Current State (Seminar Phase)
### Pain Points
1. **Hard-coded software mappings**: Windows→Linux mappings live in `configs/linux_ms_map.csv`, manually maintained
2. **Static hardware classification**: GPU/network/disk rules in `src/analysis/hw_matrix.py` are fixed heuristics
3. **Single distro target**: Configuration assumes Linux Mint; no support for Ubuntu, Fedora, Debian, etc.
4. **Limited customization**: User can choose folders/files but cannot refine software mappings before backup
5. **No audit trail**: Customizations are not recorded or reproducible

---

## 3. Desired State (Practical Phase)
### Architecture Principles
1. **Rule Engine**: Rules are data-driven, not hard-coded
2. **Customization First**: Every decision has a UI touchpoint for user override
3. **Multi-Distro**: Mapping backend adapts to target Linux distribution
4. **Confidence Scoring**: All recommendations include a confidence/reliability score
5. **Audit Trail**: User customizations are saved and reproducible
6. **Extensibility**: Organizations can define custom mappings without code changes

---

## 4. Dynamic Rule Engine Architecture

### 4.1 Rule Sources (Priority Order)
1. **System Detection**: Auto-discovered hardware/software inventory
2. **User Profile**: Operating mode (guided/balanced/expert) and preferences
3. **Target Platform**: Selected Linux distro + edition
4. **Known Mappings Database**: Community-maintained or organizational mappings
5. **User Overrides**: Custom decisions saved by user

### 4.2 Rule Engine Components
```
RuleEngine
├── HardwareClassifier (detects capabilities and support level)
├── SoftwareMapper (maps Windows apps to Linux equivalents)
├── PackageManager (adapts to apt, dnf, pacman, etc.)
├── ConfidenceScorer (rates each recommendation 0-100)
└── AuditLog (tracks user customizations)
```

### 4.3 Data Structures
#### Rule Definition (YAML-based, not hard-coded)
```yaml
rules:
  gpu_nvidia:
    condition: "gpu.vendor == 'NVIDIA'"
    recommendation: "nvidia-driver"
    confidence: 95
    notes: "Official NVIDIA driver; test after install"
    fallback: "nouille"
  
  gpu_intel:
    condition: "gpu.vendor == 'Intel'"
    recommendation: "intel-media-driver"
    confidence: 90
    notes: "Native support via i915 kernel driver"
    fallback: "xserver-xorg-video-intel"
```

#### Software Mapping (Dynamically Generated/Customized)
```json
{
  "windows_name": "Microsoft Office",
  "publisher": "Microsoft",
  "detected": true,
  "confidence": 85,
  "mappings": [
    {
      "distro": "linux-mint",
      "package_manager": "apt",
      "linux_package": "libreoffice",
      "strategy": "apt",
      "confidence": 90,
      "notes": "Full office suite replacement"
    },
    {
      "distro": "fedora",
      "package_manager": "dnf",
      "linux_package": "libreoffice",
      "strategy": "dnf",
      "confidence": 90,
      "notes": "Full office suite replacement"
    }
  ],
  "user_override": null,
  "user_confidence": null
}
```

---

## 5. Multi-Platform Linux Support

### 5.1 Distro Detection and Selection
On Linux side, auto-detect or let user choose:
```python
class LinuxDistroDetector:
    def detect_distro(self) -> tuple[str, str]:
        # Returns (distro_name, package_manager)
        # E.g. ("ubuntu", "apt"), ("fedora", "dnf"), ("arch", "pacman")
        pass
```

### 5.2 Package Manager Abstraction
```python
class PackageManagerBackend:
    """Abstract interface for package operations"""
    def install(self, packages: list[str]) -> bool:
        pass
    
    def search(self, query: str) -> list[str]:
        pass
    
    def is_installed(self, package: str) -> bool:
        pass

class AptBackend(PackageManagerBackend):
    """APT implementation (Debian/Ubuntu)"""
    
class DnfBackend(PackageManagerBackend):
    """DNF implementation (Fedora/RHEL)"""
    
class PacmanBackend(PackageManagerBackend):
    """Pacman implementation (Arch)"""
```

### 5.3 Distro-Specific Configuration
```yaml
distros:
  linux-mint:
    base: "debian"
    package_manager: "apt"
    post_install_steps:
      - "sudo apt update && sudo apt upgrade"
      - "Enable Mint Update Manager"
    notes: "Full desktop environment included"
  
  ubuntu:
    base: "debian"
    package_manager: "apt"
    editions: ["gnome", "kde", "xfce"]
    notes: "Choose edition during installation"
  
  fedora:
    base: "rpm"
    package_manager: "dnf"
    notes: "Latest upstream packages"
  
  archlinux:
    base: "arch"
    package_manager: "pacman"
    notes: "Rolling release; requires more maintenance"
```

---

## 6. Implementation Roadmap

### Phase 1.1: Extract Rules to Configuration (Week 1-2)
1. Convert hardware classification heuristics to YAML rules
2. Move software mappings to structured JSON with confidence scores
3. Create RuleEngine class that loads and applies rules dynamically
4. Add DistroDetector and PackageManagerFactory

**Deliverable**: `src/rules/` module with all hard-coded logic replaced

### Phase 1.2: Dynamic Mapping Generation (Week 2-3)
1. Implement SoftwareMapper that generates mappings at runtime
2. Add confidence scoring for each mapping
3. Create fallback recommendation system
4. Store computed mappings in memory and optionally cache to disk

**Deliverable**: Runtime-generated mapping lists with confidence scores

### Phase 2.1: User Customization UI (Week 3-4)
1. Add "Review Mappings" page in Windows wizard
2. Allow users to:
   - Accept/reject recommendations
   - Override with custom package names
   - Save custom profile for future use
3. Extend data model to track customizations

**Deliverable**: Customization page in wizard; profile save/load

### Phase 2.2: Multi-Distro Selection (Week 4-5)
1. On Linux side, add "Choose Distribution" page
2. Auto-detect if running inside installer or existing system
3. Load distro-specific rules and package mappings
4. Adjust restore flow based on selected distro

**Deliverable**: Distro selection UI; distro-specific rules applied

### Phase 3.1: Pluggable Mapping Backend (Week 5-6)
1. Create abstract MappingBackend interface
2. Implement LocalFileBackend (CSV/JSON)
3. Implement NetworkBackend (optional: pull mappings from central server)
4. Allow configuration to specify which backend to use

**Deliverable**: Swappable mapping sources; configuration-driven

---

## 7. Configuration File Schema Evolution

### Current (Hardcoded)
```yaml
migration:
  software_map_config: "linux_ms_map.csv"
```

### Target (Dynamic)
```yaml
migration:
  software_profile: "standard"  # standard | developer | custom
  distro_auto_detect: true     # or specify target: ubuntu, fedora, arch
  
rules:
  sources:
    - type: "embedded"          # Built-in rules
    - type: "local_file"        # Organization custom rules
      path: "configs/custom_mappings.json"
    - type: "network"           # Optional: central mapping service
      url: "https://mappings.example.com/api"
  
  confidence_threshold: 70      # Only auto-select if >= 70%
  
  hardware:
    enabled: true
    fallback_mode: "advisory"   # advisory | strict | ignore
  
  software:
    enabled: true
    allow_customization: true   # Can user override mappings?
    allow_unsupported: false    # Can user force unmapped software?
```

### Phase 1: Configuration File Enhancements
1. Add `rules.sources` to allow multiple mapping backends
2. Add `rules.confidence_threshold` to control automation confidence
3. Add `migration.distro_auto_detect` flag
4. Add user preference section for distro selection

---

## 8. Audit and Reproducibility

### Migration Profile (Saved by User)
```json
{
  "name": "My Work Migration",
  "created": "2026-04-16T10:00:00Z",
  "windows_config": {
    "backup_paths": ["~/Documents", "~/Desktop"],
    "file_types": [".pdf", ".docx", ".xlsx"],
    "selected_apps": ["microsoft-office", "vlc"]
  },
  "customizations": {
    "software": {
      "microsoft-office": {
        "windows_name": "Microsoft Office",
        "user_override": "libreoffice",
        "user_confidence": 95,
        "reason": "I'm familiar with LibreOffice"
      }
    }
  },
  "target": {
    "distro": "ubuntu",
    "edition": "gnome",
    "timezone": "Europe/Berlin"
  },
  "restore_config": {
    "auto_install": true,
    "package_overrides": [
      {
        "windows": "microsoft-office",
        "linux": "libreoffice",
        "action": "install"
      }
    ]
  }
}
```

### Benefits
1. Users can re-run the same migration on another system
2. Organizations can standardize profiles
3. Full audit trail of automation decisions vs. user choices

---

## 9. Data Flow Evolution

### Current Flow (Hardcoded)
```
Windows Inventory
    ↓
Hard-coded Classification (hw_matrix.py)
    ↓
Hard-coded Software Mapping (linux_ms_map.csv)
    ↓
Backup + Restore
    ↓
Static Validation
```

### Target Flow (Dynamic)
```
Windows Inventory
    ↓
[Rule Engine] Hardware Classification (rules.yaml)
    ↓
[Rule Engine] Software Mapping Generation (distro-aware)
    ↓
[User Customization] Review & Override Recommendations
    ↓
[Audit Log] Save User Profile with Customizations
    ↓
Backup + Restore (using customized profile)
    ↓
[Distro Detector] Determine Target Linux Environment
    ↓
[Rule Engine] Load Distro-Specific Rules
    ↓
[Package Manager] Resolve & Install via Correct Package Manager
    ↓
[Validation Engine] Run Post-Installation Checks
    ↓
[Evidence Report] Generate Audit Trail + Proof of Integrity
```

---

## 10. Implementation Priorities

### P0 (Critical for Practical Release)
1. Extract hardware rules to YAML (not hard-coded)
2. Extract software mappings to pluggable backend
3. Add confidence scores to all recommendations
4. Distro detection and package manager abstraction

### P1 (Essential for User Customization)
1. "Review Mappings" UI page
2. Save/load user profiles
3. Multi-distro selection page
4. Audit logging of customizations

### P2 (Enhancement for Extensibility)
1. Network-based mapping backend
2. Custom rule injection points
3. Organizational profile templates
4. Mapping conflict resolution UI

---

## 11. Testability and Validation

### Test Fixtures
- Sample inventories for common scenarios (gaming, office, developer machine)
- Known good mappings for each distro
- Hardware edge cases (unusual GPU, network, firmware)

### Test Scenarios
1. End-to-end with default mappings (all distros)
2. End-to-end with custom user overrides
3. Distro switching (same software, different package managers)
4. Confidence threshold filtering (only high-confidence automations)
5. Offline mode (pre-computed mappings, no network backend)

---

## 12. Conclusion
This strategy eliminates hard-coded assumptions and instead builds a dynamic, extensible system where rules and mappings are generated at runtime, multi-platform Linux is first-class, and users retain full control and auditability at every step. The result is a platform that is robust, customizable, and trustworthy for both individual and organizational deployments.

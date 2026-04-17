# Code Design: Dynamic Rules and Multi-Platform Implementation Examples

## 1. Overview
This document shows concrete code examples for the key architectural components that will enable dynamic rules, customization, and multi-platform support.

---

## 2. Rule Engine Component

### 2.1 Base Rule and Recommendation Classes
```python
# src/rules/base.py

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class ConfidenceLevel(Enum):
    VERY_HIGH = 95  # 90-100%
    HIGH = 80       # 80-89%
    MEDIUM = 70     # 70-79%
    LOW = 50        # 50-69%
    VERY_LOW = 30   # < 50%

@dataclass
class Recommendation:
    """A system-generated recommendation with confidence"""
    category: str                      # "gpu", "software", "network", etc.
    subject: str                       # e.g., "NVIDIA GeForce RTX 3080"
    suggested_action: str              # e.g., "nvidia-driver"
    confidence: int                    # 0-100
    explanation: str                   # Plain language reasoning
    alternatives: list[str] = None     # Fallback options
    can_override: bool = True          # User can customize?
    distro_specific: Optional[Dict] = None  # {distro: action}
    audit_id: Optional[str] = None     # For traceability

@dataclass
class UserCustomization:
    """User override of a recommendation"""
    recommendation_id: str
    original_action: str
    user_override: str
    reason: Optional[str] = None
    timestamp: str = None
    confidence_adjustment: Optional[int] = None
```

### 2.2 Rule Engine
```python
# src/rules/engine.py

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from src.rules.base import Recommendation, ConfidenceLevel
from src.loggers import get_logger

logger = get_logger("rules.engine")

class RuleEngine:
    """Dynamically loads and applies rules from configuration"""
    
    def __init__(self, rules_config_path: Path):
        self.config_path = rules_config_path
        self.rules = self._load_rules()
        self.recommendations: List[Recommendation] = []
        
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML at runtime (not hard-coded)"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def classify_gpu(self, gpu_info: Dict[str, str]) -> Recommendation:
        """Apply GPU classification rules dynamically"""
        name = gpu_info.get("Name", "").lower()
        vendor = gpu_info.get("AdapterCompatibility", "").lower()
        
        # Rules are pulled from YAML, not hard-coded
        gpu_rules = self.rules.get("gpu", {})
        
        for rule_key, rule in gpu_rules.items():
            if self._matches_condition(rule["condition"], gpu_info):
                return Recommendation(
                    category="gpu",
                    subject=gpu_info.get("Name"),
                    suggested_action=rule["recommendation"],
                    confidence=rule.get("confidence", 70),
                    explanation=rule.get("notes", ""),
                    alternatives=rule.get("fallback", []),
                    audit_id=f"gpu_{rule_key}"
                )
        
        # Fallback if no rule matched
        return Recommendation(
            category="gpu",
            subject=gpu_info.get("Name"),
            suggested_action="manual_check",
            confidence=30,
            explanation="GPU not recognized; manual verification required",
            can_override=True
        )
    
    def _matches_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate rule condition against context"""
        # Simplified example; could use eval() with safety guards
        # In production, use a proper expression language
        return eval(condition, {"__builtins__": {}}, context)
    
    def add_recommendation(self, rec: Recommendation):
        """Track generated recommendations"""
        self.recommendations.append(rec)
        logger.info(f"Recommendation: {rec.category} → {rec.suggested_action} (confidence: {rec.confidence}%)")
```

---

## 3. Software Mapping Engine

### 3.1 Software Mapping Data Structure
```python
# src/mapping/types.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class SoftwareMapping:
    """Represents a Windows app → Linux equivalent mapping"""
    windows_name: str
    publisher: str
    category: str                     # "Office", "Browser", "Media", etc.
    linux_equivalent: str             # Preferred Linux equivalent
    confidence: int                   # 0-100 (how reliable is this mapping?)
    
    # Per-distro package and strategy
    distro_packages: Dict[str, str] = field(default_factory=dict)  # {distro: package}
    distro_strategies: Dict[str, str] = field(default_factory=dict)  # {distro: strategy}
    
    notes: str = ""
    alternatives: List[str] = field(default_factory=list)
    
    # User customization
    user_override: Optional[str] = None
    user_confidence_adjustment: Optional[int] = None
    
    # Audit trail
    source: str = "embedded"  # "embedded", "custom", "network"
    version: str = "1.0"
    last_updated: str = None

@dataclass
class SoftwareMappingDatabase:
    """Collection of all mappings with search capabilities"""
    mappings: List[SoftwareMapping] = field(default_factory=list)
    
    def find_by_windows_name(self, name: str) -> Optional[SoftwareMapping]:
        """Find mapping by Windows application name"""
        name_lower = name.lower()
        for m in self.mappings:
            if name_lower in m.windows_name.lower():
                return m
        return None
    
    def get_for_distro(self, distro: str) -> List[SoftwareMapping]:
        """Get mappings applicable to a specific distro"""
        return [m for m in self.mappings if distro in m.distro_packages]
    
    def filter_by_confidence(self, threshold: int) -> List[SoftwareMapping]:
        """Get only high-confidence mappings"""
        return [m for m in self.mappings if m.confidence >= threshold]
```

### 3.2 Dynamic Mapping Generator
```python
# src/mapping/generator.py

import json
from pathlib import Path
from typing import List, Dict, Optional
from src.mapping.types import SoftwareMapping, SoftwareMappingDatabase
from src.loggers import get_logger

logger = get_logger("mapping.generator")

class MappingGenerator:
    """Generates software mappings dynamically based on inventory and target distro"""
    
    def __init__(self, base_mapping_path: Path):
        self.base_mappings = self._load_base_mappings(base_mapping_path)
        self.database = SoftwareMappingDatabase()
    
    def _load_base_mappings(self, path: Path) -> List[Dict]:
        """Load from JSON or CSV (not hard-coded)"""
        if path.suffix == ".json":
            with open(path, 'r') as f:
                return json.load(f)
        elif path.suffix == ".csv":
            import csv
            with open(path, 'r') as f:
                return list(csv.DictReader(f))
        return []
    
    def generate_for_detected_software(
        self, 
        detected_apps: List[str], 
        target_distro: str
    ) -> SoftwareMappingDatabase:
        """
        For each detected Windows app, generate distro-specific mappings.
        This replaces the hard-coded approach.
        """
        mappings = []
        
        for app_name in detected_apps:
            base = self._find_base_mapping(app_name)
            if not base:
                logger.debug(f"No mapping found for {app_name}")
                continue
            
            # Generate distro-specific packages
            distro_packages = self._resolve_packages_for_distro(base, target_distro)
            
            mapping = SoftwareMapping(
                windows_name=base.get("windows_name"),
                publisher=base.get("publisher", ""),
                category=base.get("category", "Other"),
                linux_equivalent=distro_packages.get(target_distro, ""),
                confidence=int(base.get("confidence", 70)),
                distro_packages={target_distro: distro_packages.get(target_distro)},
                distro_strategies={target_distro: base.get("migration_strategy", "apt")},
                notes=base.get("notes", ""),
                alternatives=base.get("alternatives", []),
                source="generated"
            )
            mappings.append(mapping)
        
        self.database.mappings = mappings
        logger.info(f"Generated {len(mappings)} mappings for {target_distro}")
        return self.database
    
    def _find_base_mapping(self, app_name: str) -> Optional[Dict]:
        """Search base mappings for app"""
        app_lower = app_name.lower()
        for m in self.base_mappings:
            if app_lower in m.get("windows_name", "").lower():
                return m
        return None
    
    def _resolve_packages_for_distro(self, base_mapping: Dict, distro: str) -> Dict[str, str]:
        """Resolve the correct package for target distro"""
        # Example: different distros may need different package names
        distro_map = {
            "ubuntu": base_mapping.get("ubuntu_package") or base_mapping.get("linux_package"),
            "fedora": base_mapping.get("fedora_package") or base_mapping.get("linux_package"),
            "arch": base_mapping.get("arch_package") or base_mapping.get("linux_package"),
        }
        return {distro: distro_map.get(distro, base_mapping.get("linux_package"))}
```

---

## 4. Package Manager Abstraction

### 4.1 Package Manager Interface
```python
# src/package/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from enum import Enum

class InstallStrategy(Enum):
    APT = "apt"      # Debian/Ubuntu
    DNF = "dnf"      # Fedora/RHEL
    PACMAN = "pacman"  # Arch
    MANUAL = "manual"  # User must install manually

class PackageManagerBackend(ABC):
    """Abstract interface for package management operations"""
    
    @abstractmethod
    def install(self, packages: List[str], sudo: bool = True) -> Tuple[bool, str]:
        """Install packages; return (success, output)"""
        pass
    
    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """Check if package is already installed"""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[str]:
        """Search for packages matching query"""
        pass
    
    @abstractmethod
    def get_alternative(self, package: str) -> Optional[str]:
        """Get alternative package if primary not found"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return strategy identifier"""
        pass
```

### 4.2 APT Implementation
```python
# src/package/apt.py

from src.package.base import PackageManagerBackend, InstallStrategy
import subprocess
from typing import List, Tuple, Optional

class AptBackend(PackageManagerBackend):
    """Implementation for Debian/Ubuntu (apt)"""
    
    def install(self, packages: List[str], sudo: bool = True) -> Tuple[bool, str]:
        """Install packages using apt-get"""
        if not packages:
            return True, "No packages to install"
        
        cmd = []
        if sudo:
            cmd.append("pkexec")
        cmd.extend(["apt-get", "install", "-y"] + packages)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed"""
        try:
            result = subprocess.run(
                ["dpkg", "-l", package],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def search(self, query: str) -> List[str]:
        """Search for packages"""
        try:
            result = subprocess.run(
                ["apt-cache", "search", query],
                capture_output=True,
                text=True
            )
            return [line.split()[0] for line in result.stdout.split('\n') if line]
        except:
            return []
    
    def get_alternative(self, package: str) -> Optional[str]:
        """Fallback logic for alternative packages"""
        # Example: if libreoffice fails, suggest openoffice
        alternatives = {
            "libreoffice": "openoffice",
            "firefox": "chromium",
            "vlc": "mpv"
        }
        return alternatives.get(package)
    
    def get_strategy_name(self) -> str:
        return "apt"
```

### 4.3 DNF Implementation
```python
# src/package/dnf.py

from src.package.base import PackageManagerBackend, InstallStrategy
import subprocess
from typing import List, Tuple, Optional

class DnfBackend(PackageManagerBackend):
    """Implementation for Fedora/RHEL (dnf)"""
    
    def install(self, packages: List[str], sudo: bool = True) -> Tuple[bool, str]:
        """Install packages using dnf"""
        if not packages:
            return True, "No packages to install"
        
        cmd = []
        if sudo:
            cmd.append("pkexec")
        cmd.extend(["dnf", "install", "-y"] + packages)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed"""
        try:
            result = subprocess.run(
                ["rpm", "-q", package],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def search(self, query: str) -> List[str]:
        """Search for packages"""
        try:
            result = subprocess.run(
                ["dnf", "search", query],
                capture_output=True,
                text=True
            )
            return [line.split()[0] for line in result.stdout.split('\n') if line]
        except:
            return []
    
    def get_alternative(self, package: str) -> Optional[str]:
        """Fallback logic"""
        alternatives = {
            "libreoffice": "openoffice",
            "firefox": "chromium",
            "vlc": "mpv"
        }
        return alternatives.get(package)
    
    def get_strategy_name(self) -> str:
        return "dnf"
```

### 4.4 Package Manager Factory
```python
# src/package/factory.py

from src.package.base import PackageManagerBackend, InstallStrategy
from src.package.apt import AptBackend
from src.package.dnf import DnfBackend
from typing import Optional

class PackageManagerFactory:
    """Factory for creating appropriate package manager backend"""
    
    _backends = {
        "apt": AptBackend,
        "dnf": DnfBackend,
        # TODO: Add pacman, zypper, etc.
    }
    
    @staticmethod
    def create(strategy: str) -> Optional[PackageManagerBackend]:
        """Get backend for package manager strategy"""
        backend_class = PackageManagerFactory._backends.get(strategy)
        if backend_class:
            return backend_class()
        return None
    
    @staticmethod
    def detect_available() -> Optional[str]:
        """Auto-detect available package manager on current system"""
        import subprocess
        
        # Try to detect in order of preference
        for cmd in ["apt-get", "dnf", "pacman"]:
            try:
                subprocess.run(["which", cmd], capture_output=True, check=True)
                return cmd
            except:
                continue
        
        return None
```

---

## 5. Distro Detection and Configuration

### 5.1 Distro Detector
```python
# src/distro/detector.py

from typing import Tuple, Optional
import subprocess
from src.loggers import get_logger

logger = get_logger("distro.detector")

class DistroDetector:
    """Detect Linux distribution and package manager"""
    
    @staticmethod
    def detect() -> Tuple[str, str]:
        """
        Detect distro and package manager.
        Returns: (distro_name, package_manager)
        """
        # Method 1: Try /etc/os-release (modern distros)
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
                os_info = {line.split("=")[0]: line.split("=")[1].strip() 
                          for line in lines if "=" in line}
                
                distro_id = os_info.get("ID", "").lower()
                distro_name = os_info.get("NAME", "")
                
                pm = DistroDetector._map_distro_to_pm(distro_id)
                logger.info(f"Detected: {distro_name} (package manager: {pm})")
                return distro_id, pm
        except Exception as e:
            logger.warning(f"Failed to read /etc/os-release: {e}")
        
        # Method 2: Try lsb_release
        try:
            result = subprocess.run(["lsb_release", "-si"], capture_output=True, text=True)
            distro_name = result.stdout.strip().lower()
            pm = DistroDetector._map_distro_to_pm(distro_name)
            logger.info(f"Detected (lsb): {distro_name} → {pm}")
            return distro_name, pm
        except Exception:
            pass
        
        # Fallback
        logger.warning("Could not auto-detect distro; assuming Ubuntu/apt")
        return "ubuntu", "apt"
    
    @staticmethod
    def _map_distro_to_pm(distro: str) -> str:
        """Map distro name to package manager"""
        mapping = {
            "ubuntu": "apt",
            "debian": "apt",
            "linuxmint": "apt",
            "fedora": "dnf",
            "rhel": "dnf",
            "centos": "dnf",
            "arch": "pacman",
            "manjaro": "pacman",
            "opensuse": "zypper",
        }
        return mapping.get(distro.lower(), "apt")  # apt as fallback
```

### 5.2 Distro Configuration
```python
# src/distro/config.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import yaml
from pathlib import Path

@dataclass
class DistroConfig:
    """Configuration for a specific Linux distribution"""
    name: str
    code_name: str
    base_distro: str              # "debian", "rpm", "arch"
    package_manager: str          # "apt", "dnf", "pacman"
    editions: List[str] = field(default_factory=list)
    post_install_steps: List[str] = field(default_factory=list)
    notes: str = ""
    
    def __hash__(self):
        return hash(self.name)

class DistroConfigLoader:
    """Load distro configurations from YAML (dynamic, not hard-coded)"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.distros: Dict[str, DistroConfig] = self._load()
    
    def _load(self) -> Dict[str, DistroConfig]:
        """Load distro configurations from YAML"""
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        
        distros = {}
        for name, config in data.get("distros", {}).items():
            distros[name] = DistroConfig(
                name=name,
                code_name=config.get("code_name", ""),
                base_distro=config.get("base", ""),
                package_manager=config.get("package_manager", ""),
                editions=config.get("editions", []),
                post_install_steps=config.get("post_install_steps", []),
                notes=config.get("notes", "")
            )
        
        return distros
    
    def get(self, name: str) -> Optional[DistroConfig]:
        """Get config for specific distro"""
        return self.distros.get(name)
    
    def list_all(self) -> List[str]:
        """List all configured distros"""
        return list(self.distros.keys())
```

---

## 6. User Customization and Audit Trail

### 6.1 Customization Manager
```python
# src/customization/manager.py

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
from src.mapping.types import SoftwareMapping
from src.loggers import get_logger

logger = get_logger("customization.manager")

class CustomizationManager:
    """Manage user customizations and save reproducible profiles"""
    
    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.customizations: Dict[str, str] = {}  # {mapping_id: user_override}
    
    def record_override(self, mapping_id: str, user_choice: str, reason: str = ""):
        """Record a user customization"""
        self.customizations[mapping_id] = {
            "user_choice": user_choice,
            "reason": reason,
            "timestamp": str(datetime.now())
        }
        logger.info(f"Customization recorded: {mapping_id} → {user_choice}")
    
    def save_profile(self, profile_name: str, metadata: Dict) -> Path:
        """Save migration profile with all customizations"""
        profile_data = {
            "name": profile_name,
            "created": str(datetime.now()),
            "customizations": self.customizations,
            "metadata": metadata
        }
        
        profile_path = self.profile_dir / f"{profile_name}.json"
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        logger.info(f"Profile saved: {profile_path}")
        return profile_path
    
    def load_profile(self, profile_path: Path) -> Dict:
        """Load previously saved profile"""
        with open(profile_path) as f:
            return json.load(f)
    
    def list_saved_profiles(self) -> List[Path]:
        """List all saved migration profiles"""
        return list(self.profile_dir.glob("*.json"))
```

---

## 7. Usage Example: Window Desktop Customization Page

```python
# src/ui/pages/software_customization.py

import tkinter as tk
import ttkbootstrap as ttk
from src.ui.core import BasePage
from src.mapping.types import SoftwareMappingDatabase
from src.customization.manager import CustomizationManager

class SoftwareCustomizationPage(BasePage):
    """Allow users to review and customize software mappings"""
    
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.header["text"] = "Review and Customize Software Mappings"
        
        # Get generated mappings from controller state
        self.mappings: SoftwareMappingDatabase = controller.state.get("generated_mappings")
        self.customization_manager = CustomizationManager(Path("data/profiles"))
        
        self._build_ui()
    
    def _build_ui(self):
        """Build customization interface"""
        
        # Instructions
        ttk.Label(
            self.body,
            text="These mappings were automatically detected. You can customize any of them below.",
            wraplength=800
        ).pack(anchor="w", pady=10)
        
        # Scrollable list of mappings
        frame_mappings = ttk.Frame(self.body)
        frame_mappings.pack(fill="both", expand=True, pady=10)
        
        for mapping in self.mappings.mappings:
            self._add_mapping_row(frame_mappings, mapping)
        
        # Buttons
        ttk.Button(
            self.body,
            text="Save Profile",
            command=self._save_profile
        ).pack(anchor="e", pady=10)
    
    def _add_mapping_row(self, parent, mapping):
        """Create customizable UI for one mapping"""
        
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=5)
        
        # Windows app name
        ttk.Label(row, text=f"{mapping.windows_name}", font=("bold",)).pack(side="left", padx=5)
        
        # Default recommendation
        default_label = ttk.Label(row, text=f"→ {mapping.linux_equivalent}", foreground="blue")
        default_label.pack(side="left", padx=5)
        
        # Confidence
        ttk.Label(row, text=f"({mapping.confidence}% confidence)").pack(side="left", padx=5)
        
        # Custom entry
        custom_var = tk.StringVar(value=mapping.linux_equivalent)
        custom_entry = ttk.Entry(row, textvariable=custom_var, width=20)
        custom_entry.pack(side="left", padx=5)
        
        # Store for later
        mapping.user_override = custom_var
    
    def before_leave(self):
        """Save customizations before moving forward"""
        
        for mapping in self.mappings.mappings:
            if hasattr(mapping, 'user_override'):
                override_value = mapping.user_override.get()
                if override_value != mapping.linux_equivalent:
                    mapping.user_override = override_value
                    self.customization_manager.record_override(
                        mapping.windows_name,
                        override_value,
                        reason="User customized before backup"
                    )
        
        return True
```

---

## 8. Conclusion
These code components form the foundation for a truly dynamic, customizable, multi-platform migration system. Key benefits:

1. **No Hard-Coded Rules**: Everything loads from YAML/JSON at runtime
2. **User Customization**: Every recommendation can be overridden via UI
3. **Multi-Platform**: Pluggable package managers and distro-specific configurations
4. **Audit Trail**: All customizations tracked and saved as reproducible profiles
5. **Extensibility**: Organizations can inject custom rules without modifying code

This architecture enables the platform to grow and adapt without requiring code changes for new hardware, new distros, or new software mappings.

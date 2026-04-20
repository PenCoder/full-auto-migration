"""Package-manager abstraction used by restore and recommendation workflows."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from src.orchestration.errors import ERR_PACKAGE_INSTALL, ERR_UNSUPPORTED_PM, MigrationError


@dataclass
class PackageInstallResult:
    """Summary of a package installation run."""
    manager: str
    installed: list[str]
    failed: list[str]
    stdout: str
    stderr: str


def detect_package_manager(preferred_distro: str | None = None) -> str:
    """Detect the best supported package manager for the current environment."""
    distro = (preferred_distro or "").lower()
    if "ubuntu" in distro or "mint" in distro or "debian" in distro:
        return "apt"
    if "fedora" in distro or "rhel" in distro:
        return "dnf"
    if "arch" in distro or "manjaro" in distro:
        return "pacman"

    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"

    raise MigrationError(ERR_UNSUPPORTED_PM, "No supported package manager found")


def install_packages(packages: list[str], manager: str, use_pkexec: bool = True) -> PackageInstallResult:
    """Install packages through the selected package manager."""
    if not packages:
        return PackageInstallResult(manager=manager, installed=[], failed=[], stdout="", stderr="")

    if manager == "apt":
        base = ["apt-get", "install", "-y"]
    elif manager == "dnf":
        base = ["dnf", "install", "-y"]
    elif manager == "pacman":
        base = ["pacman", "-S", "--noconfirm"]
    else:
        raise MigrationError(ERR_UNSUPPORTED_PM, manager)

    cmd = base + packages
    if use_pkexec:
        cmd = ["pkexec"] + cmd

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise MigrationError(ERR_PACKAGE_INSTALL, stderr.strip() or "Unknown package install failure")

    return PackageInstallResult(
        manager=manager,
        installed=packages,
        failed=[],
        stdout=stdout,
        stderr=stderr,
    )

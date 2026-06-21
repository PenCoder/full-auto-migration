"""Package-manager abstraction used by restore and recommendation workflows."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

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


def _base_command(manager: str, verb: str) -> list[str]:
    if manager == "apt":
        return ["apt-get", "install", "-y"] if verb == "install" else ["apt-get", "remove", "-y"]
    if manager == "dnf":
        return ["dnf", "install", "-y"] if verb == "install" else ["dnf", "remove", "-y"]
    if manager == "pacman":
        return ["pacman", "-S", "--noconfirm"] if verb == "install" else ["pacman", "-R", "--noconfirm"]
    raise MigrationError(ERR_UNSUPPORTED_PM, manager)


_OPERATION_TIMEOUT_SECONDS = 120


def _run_package_operation(
    packages: list[str],
    manager: str,
    verb: str,
    use_pkexec: bool,
    on_progress: Optional[Callable[[str, int, int], None]],
) -> PackageInstallResult:
    """Shared batch-then-per-package-fallback runner for install/remove.

    apt-get/dnf/pacman act on their whole package list as one atomic
    transaction — if even one name is invalid or unremovable, the whole
    batch fails and nothing happens, including otherwise-valid packages.
    Falls back to operating one package at a time when the batch attempt
    fails, so a single bad name doesn't sink every other valid one.

    The one-at-a-time fallback re-pays each package manager's per-invocation
    overhead (re-reading package lists, resolving dependencies), so it's
    noticeably slower than the batch path — on_progress(pkg, index, total)
    is called before each individual attempt so callers can surface that
    it's still working rather than appearing to hang.

    Every attempt is bounded by a timeout: pkexec needs a polkit agent to
    answer its elevation request, and if that request never gets answered
    (no agent reachable, dialog never shown, session issue) the subprocess
    blocks indefinitely with nothing to show for it. A timed-out attempt is
    treated as a normal failure for that package/batch, not a hang.
    """
    if not packages:
        return PackageInstallResult(manager=manager, installed=[], failed=[], stdout="", stderr="")

    base = _base_command(manager, verb)

    def run(targets: list[str]) -> tuple[int, str, str]:
        cmd = base + targets
        if use_pkexec:
            cmd = ["pkexec"] + cmd
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=_OPERATION_TIMEOUT_SECONDS)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return -1, "", (
                f"Timed out after {_OPERATION_TIMEOUT_SECONDS}s waiting for a response "
                "(likely an unanswered elevation/authentication prompt)."
            )

    code, stdout, stderr = run(packages)
    if code == 0:
        return PackageInstallResult(manager=manager, installed=list(packages), failed=[], stdout=stdout, stderr=stderr)

    installed: list[str] = []
    failed: list[str] = []
    stdout_parts = [stdout]
    stderr_parts = [stderr]
    total = len(packages)
    for index, pkg in enumerate(packages, start=1):
        if on_progress:
            on_progress(pkg, index, total)
        pkg_code, pkg_stdout, pkg_stderr = run([pkg])
        stdout_parts.append(pkg_stdout)
        stderr_parts.append(pkg_stderr)
        (installed if pkg_code == 0 else failed).append(pkg)

    if not installed:
        raise MigrationError(ERR_PACKAGE_INSTALL, stderr.strip() or "Unknown package operation failure")

    return PackageInstallResult(
        manager=manager,
        installed=installed,
        failed=failed,
        stdout="\n".join(stdout_parts),
        stderr="\n".join(stderr_parts),
    )


def install_packages(
    packages: list[str],
    manager: str,
    use_pkexec: bool = True,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> PackageInstallResult:
    """Install packages through the selected package manager. See _run_package_operation."""
    return _run_package_operation(packages, manager, "install", use_pkexec, on_progress)


def remove_packages(
    packages: list[str],
    manager: str,
    use_pkexec: bool = True,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> PackageInstallResult:
    """Uninstall packages through the selected package manager.

    Uses plain remove (not purge/autoremove) — removes exactly the named
    packages and leaves their config files and any shared dependencies
    other software relies on untouched.
    """
    return _run_package_operation(packages, manager, "remove", use_pkexec, on_progress)

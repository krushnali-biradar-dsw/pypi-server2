#!/usr/bin/env python3
"""
Differential Dependency Sync Script.
Compares requirements.txt with packages inside pyrepo/ and downloads only missing or updated packages.
"""

import os
import sys
import re
import subprocess
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("  Differential Dependency Sync (Offline PyPI Prep)")
    print("=" * 60)

def parse_requirements(req_path):
    """Parses requirements.txt to return a list of package specs."""
    if not os.path.exists(req_path):
        print(f"Error: {req_path} not found.")
        return []
    
    specs = []
    with open(req_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignore comments and empty lines
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            specs.append(line)
    return specs

def get_downloaded_packages(pyrepo_path):
    """Lists already downloaded packages in the pyrepo directory."""
    if not os.path.exists(pyrepo_path):
        os.makedirs(pyrepo_path, exist_ok=True)
        return set()
    
    files = os.listdir(pyrepo_path)
    downloaded = set()
    for filename in files:
        if filename.endswith((".whl", ".tar.gz", ".zip")):
            # Extract package name by converting dashes/underscores and splitting before version
            # E.g., autogen-0.2.27-py3-none-any.whl -> autogen
            # E.g., pyautogen-0.2.27.tar.gz -> pyautogen
            name_part = filename.split("-")[0]
            # Normalize package name (lowercase, replace underscores with dashes)
            name_norm = name_part.lower().replace("_", "-")
            downloaded.add(name_norm)
    return downloaded

def sync():
    print_banner()
    
    root_dir = Path(__file__).resolve().parent
    req_path = root_dir / "component" / "requirements.txt"
    pyrepo_path = root_dir / "pyrepo"
    
    requirements = parse_requirements(req_path)
    if not requirements:
        print("No requirements to sync.")
        return
    
    print(f"Found {len(requirements)} packages defined in requirements.txt.")
    downloaded = get_downloaded_packages(pyrepo_path)
    print(f"Currently {len(downloaded)} packages downloaded in pyrepo/.")
    
    missing = []
    for req in requirements:
        # Extract base package name (e.g. pyautogen==0.2.27 -> pyautogen)
        match = re.match(r"^([a-zA-Z0-9_\-]+)", req)
        if match:
            pkg_name = match.group(1).lower().replace("_", "-")
            if pkg_name not in downloaded:
                missing.append(req)
            else:
                print(f"[OK] Package '{pkg_name}' is already cached in pyrepo/.")
        else:
            missing.append(req)
            
    if not missing:
        print("\nAll dependencies are fully synced in pyrepo/! Nothing to download.")
        return
    
    print(f"\nMissing dependencies to download: {missing}")
    print("Downloading missing dependencies and their transient dependencies...")
    
    # We run pip download for the missing packages
    # We specify --find-links so pip will resolve transient dependencies from pyrepo/ if available
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(pyrepo_path),
        "--find-links", str(pyrepo_path),
        "--only-binary=:all:",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.10"
    ]
    # Log the targeting parameters
    print("Forcing Linux x86_64 Python 3.10 pre-compiled binary wheels...")
        
    for m in missing:
        cmd.append(m)
        
    print(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\nDifferential sync completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\nError running pip download: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync()

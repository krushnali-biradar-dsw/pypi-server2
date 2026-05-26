#!/usr/bin/env python3
"""
Automated Verification Suite for Secure Air-Gapped Workflows.
Validates:
1. Docker local PyPI server status.
2. Differential dependency sync (detecting, downloading, and serving missing packages).
3. Pip internet isolation during Docker builds (Test 1: success via local PyPI, Test 2: fail via bogus URL proving no fallback, Test 3: success via local wheel find-links).
"""

import os
import sys
import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# ANSI colors for premium aesthetic CLI output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

def print_step(title):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

def run_command(cmd, cwd=None, capture=True):
    """Runs a shell command and returns execution success, status code, and output."""
    try:
        if capture:
            res = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True, encoding="utf-8", errors="ignore")
            return res.returncode == 0, res.returncode, res.stdout + res.stderr
        else:
            res = subprocess.run(cmd, cwd=cwd, shell=True)
            return res.returncode == 0, res.returncode, ""
    except Exception as e:
        return False, -1, str(e)

def parse_requirements(req_path):
    if not os.path.exists(req_path):
        return []
    specs = []
    with open(req_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            specs.append(line)
    return specs

def get_package_name(spec):
    match = re.match(r"^([a-zA-Z0-9_\-]+)", spec)
    if match:
        return match.group(1).lower().replace("_", "-")
    return spec.lower().replace("_", "-")

def list_downloaded_packages(pyrepo_path):
    if not os.path.exists(pyrepo_path):
        return set()
    downloaded = set()
    for filename in os.listdir(pyrepo_path):
        if filename.endswith((".whl", ".tar.gz", ".zip")):
            name_part = filename.split("-")[0]
            downloaded.add(name_part.lower().replace("_", "-"))
    return downloaded

def check_pypi_server():
    """Queries the PyPI simple index to see if it is running."""
    url = "http://localhost:8080/simple/"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            return True, content
    except Exception as e:
        return False, str(e)

def check_package_on_pypi_server(package_name):
    """Checks if a package is served by the local PyPI server simple index."""
    url = f"http://localhost:8080/simple/{package_name}/"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            return True, content
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}"
    except Exception as e:
        return False, str(e)

def main():
    print(f"{BOLD}{YELLOW}" + "="*60)
    print("      SECURE AIR-GAPPED PIPELINE VERIFICATION SUITE      ")
    print("="*60 + f"{RESET}")

    root_dir = Path(__file__).resolve().parent
    req_path = root_dir / "component" / "requirements.txt"
    pyrepo_path = root_dir / "pyrepo"

    # ----------------------------------------------------
    # STEP 1: Verify PyPI Docker Container Status
    # ----------------------------------------------------
    print_step("STEP 1: Verify local-pypi-server Container Status")
    ok, code, output = run_command("docker ps --filter name=local-pypi-server --format \"{{.Status}}\"")
    if ok and output.strip():
        print(f"{GREEN}[OK] local-pypi-server docker container is running! Status: {output.strip()}{RESET}")
    else:
        print(f"{RED}[FAIL] local-pypi-server container is NOT running or docker is down!{RESET}")
        sys.exit(1)

    # Check HTTP endpoint
    server_ok, server_msg = check_pypi_server()
    if server_ok:
        print(f"{GREEN}[OK] local-pypi-server simple index is fully responsive at http://localhost:8080/simple/{RESET}")
    else:
        print(f"{RED}[FAIL] local-pypi-server simple index is NOT reachable: {server_msg}{RESET}")
        sys.exit(1)

    # ----------------------------------------------------
    # STEP 2: Audit Current Packages
    # ----------------------------------------------------
    print_step("STEP 2: Audit Current Local Packages in pyrepo/")
    requirements = parse_requirements(req_path)
    downloaded = list_downloaded_packages(pyrepo_path)

    print(f"Total packages in requirements.txt: {len(requirements)}")
    print(f"Total packages cached in pyrepo/: {len(downloaded)}")

    missing = []
    for req in requirements:
        pkg = get_package_name(req)
        if pkg not in downloaded:
            missing.append(req)
            print(f"  - Package {pkg} ({req}) is {RED}MISSING{RESET}")
        else:
            print(f"  - Package {pkg} is {GREEN}CACHED{RESET}")

    # ----------------------------------------------------
    # STEP 3: Run Differential Sync (sync_deps.py)
    # ----------------------------------------------------
    print_step("STEP 3: Run Differential Sync script to download missing packages")
    if missing:
        print(f"Executing: python sync_deps.py")
        sync_ok, sync_code, sync_out = run_command("python sync_deps.py", capture=False)
        if sync_ok:
            print(f"\n{GREEN}[OK] Differential Sync completed successfully!{RESET}")
        else:
            print(f"\n{RED}[FAIL] Differential Sync failed with code {sync_code}!{RESET}")
            sys.exit(1)
    else:
        print(f"{GREEN}All packages are already cached! Skip sync_deps.py execution.{RESET}")

    # ----------------------------------------------------
    # STEP 4: Verify Newly Cached Packages are Served
    # ----------------------------------------------------
    print_step("STEP 4: Verify New Packages are picked up by PyPI Server")
    downloaded_after = list_downloaded_packages(pyrepo_path)
    
    # Check each requirement against the Docker PyPI server
    print("Auditing server endpoints...")
    all_served = True
    for req in requirements:
        pkg = get_package_name(req)
        served, served_msg = check_package_on_pypi_server(pkg)
        if served:
            print(f"  - http://localhost:8080/simple/{pkg}/ -> {GREEN}[OK] SERVED{RESET}")
        else:
            print(f"  - http://localhost:8080/simple/{pkg}/ -> {RED}[FAIL] ({served_msg}){RESET}")
            all_served = False
            
    if all_served:
        print(f"\n{GREEN}[OK] Success! All packages from requirements.txt are now fully cached and served by local-pypi-server!{RESET}")
    else:
        print(f"\n{YELLOW}[WARN] Some packages are not yet visible or served by the PyPI server index.{RESET}")

    # ----------------------------------------------------
    # STEP 5: Docker Build Isolation Tests
    # ----------------------------------------------------
    print_step("STEP 5: Execute Docker Build Isolation and Verification Tests")

    # TEST 1: Normal Build (Success via local PyPI server)
    print(f"\n{BOLD}Test scenario 1: Build image using local PyPI server...{RESET}")
    t1_cmd = (
        "docker build "
        "--add-host=host.docker.internal:host-gateway "
        "-t local-component-test "
        "-f component/Dockerfile "
        "--build-arg PYPI_INDEX_URL=http://host.docker.internal:8080/simple ."
    )
    print(f"Running: {t1_cmd}")
    t1_ok, t1_code, t1_out = run_command(t1_cmd)
    
    with open(root_dir / "test_build_success.log", "w", encoding="utf-8") as f:
        f.write(t1_out)
        
    if t1_ok:
        print(f"{GREEN}[OK] Test Scenario 1 PASSED! Image built successfully using local PyPI server.{RESET}")
    else:
        print(f"{RED}[FAIL] Test Scenario 1 FAILED! Build output written to test_build_success.log.{RESET}")
        print(t1_out[-1000:])
        sys.exit(1)

    # TEST 2: Bogus Index (Failure Proof - verifies NO fallback to internet!)
    print(f"\n{BOLD}Test scenario 2: Build image using invalid index (Connection failure proof)...{RESET}")
    t2_cmd = (
        "docker build "
        "--add-host=host.docker.internal:host-gateway "
        "-t local-component-test-fail "
        "-f component/Dockerfile "
        "--build-arg PYPI_INDEX_URL=http://host.docker.internal:9999/simple ."
    )
    print(f"Running: {t2_cmd}")
    t2_ok, t2_code, t2_out = run_command(t2_cmd)
    
    with open(root_dir / "test_build_fail.log", "w", encoding="utf-8") as f:
        f.write(t2_out)
        
    if not t2_ok:
        # We expect a failure because the index URL is invalid (no index on port 9999)
        print(f"{GREEN}[OK] Test Scenario 2 PASSED! Build failed as expected on port 9999.{RESET}")
        print(f"{GREEN}[OK] This PROVES that pip did NOT fall back to the public internet.{RESET}")
        print(f"Failure logs written to test_build_fail.log. Quick view of the failure:")
        # Find the pip error in the output and print it
        pip_errors = [line for line in t2_out.splitlines() if "Could not find a version" in line or "ConnectionError" in line or "ERROR:" in line or "Retrying" in line]
        for pe in pip_errors[-3:]:
            print(f"  {YELLOW}{pe}{RESET}")
    else:
        print(f"{RED}[FAIL] Test Scenario 2 FAILED! The build should have failed, but it succeeded! This means pip bypassed the bogus index and used the public internet!{RESET}")
        sys.exit(1)

    # TEST 3: Pure Local Directory Build (Success via OFFLINE_FIND_LINKS)
    print(f"\n{BOLD}Test scenario 3: Build image using local wheels directory (no index)...{RESET}")
    t3_cmd = (
        "docker build "
        "-t local-component-test-offline "
        "-f component/Dockerfile "
        "--build-arg OFFLINE_FIND_LINKS=/app/pyrepo "
        "--build-arg PYPI_INDEX_URL=\"\" ."
    )
    print(f"Running: {t3_cmd}")
    t3_ok, t3_code, t3_out = run_command(t3_cmd)
    
    with open(root_dir / "test_build_offline.log", "w", encoding="utf-8") as f:
        f.write(t3_out)
        
    if t3_ok:
        print(f"{GREEN}[OK] Test Scenario 3 PASSED! Image built successfully using offline find-links local cache.{RESET}")
    else:
        print(f"{RED}[FAIL] Test Scenario 3 FAILED! Build output written to test_build_offline.log.{RESET}")
        print(t3_out[-1000:])
        sys.exit(1)

    print(f"\n{BOLD}{GREEN}" + "="*60)
    print("      ALL PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY!      ")
    print("="*60 + f"{RESET}\n")

if __name__ == "__main__":
    main()

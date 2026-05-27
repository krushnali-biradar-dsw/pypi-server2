# End-to-End Secure Air-Gapped CI/CD Pipeline & Dependency Management

This documentation details the conceptual architecture, component setup, and execution workflows of the secure, internet-isolated application build and deployment system. 

---

## 1. Architectural Overview

The system is designed for **air-gapped and high-security deployment environments** where target containers must be built and run without direct access to the public internet (PyPI). The architecture consists of three core layers:

```
[ Developer Workspace ]            [ Local PyPI Environment ]            [ CI/CD Runner (GHA) ]
  requirements.txt                   Docker PyPI Container                 GitHub Actions Cache
         │                                       │                                   │
         ▼                                       ▼                                   ▼
┌──────────────────┐               ┌──────────────────────────┐         ┌──────────────────────────┐
│  Dependency Sync │ ────────────> │ Mounted Packages Folder  │ <─────> │  Dynamic Runner Cache    │
└──────────────────┘               └──────────────────────────┘         └──────────────────────────┘
                                                 │                                   │
                                                 ▼                                   ▼
                                   ┌──────────────────────────┐         ┌──────────────────────────┐
                                   │ Isolated Docker Build    │         │ Isolated Actions Build   │
                                   │ (Private PyPI Index)     │         │ (Pure Directory Cache)   │
                                   └──────────────────────────┘         └──────────────────────────┘
```

1. **Dependency Sync Layer**: Computes differences between requirements and cached packages, downloading only new wheels.
2. **Private Package Server Layer**: A local dockerized index serving cached wheels to the builder host.
3. **Isolated Image Build Layer**: A Docker container build process configured to consume dependencies exclusively from the private index or local cached folders.

---

## 2. Component Setup & Responsibilities

### Component A: Local PyPI Server (`docker-compose.yml`)
* **Role**: Runs a lightweight PyPI server container mapped to a local host directory.
* **Volume Mapping**: Mounts the host's package cache directory directly to the container's package folder. This ensures that any wheel downloaded on the host is immediately scanned and served by the PyPI container without requiring manual uploads or service restarts.
* **Security**: Configured to run in unauthenticated read-write mode internally to support rapid local integration testing.

### Component B: Differential Dependency Sync Script (`sync_deps.py`)
* **Role**: Governs package pre-fetching and caching.
* **Operation**:
  1. Parses the application's requirement list.
  2. Scans the local wheel cache folder and extracts package names.
  3. Identifies which requirements (or specific versions) are not present in the cache.
  4. Triggers a secure targeted download for the missing packages and their transient dependencies.
  5. Targets Linux x86_64 pre-compiled binary wheel formats specifically to ensure compatibility inside the slim production Docker container.

### Component C: Secure Dockerfile (`component/Dockerfile`)
* **Role**: Builds the secure production container image under strict internet-isolation parameters.
* **Isolation Configuration**: 
  * Completely removes default public internet update stages.
  * Dynamically checks for local offline wheel directory inputs or a private PyPI index URL.
  * If a private index URL is provided, it configures `pip` to use **only** that specific index, disabling default public fallback channels.
  * If a local wheel cache is provided, it uses the strict `pip` `--no-index` installation flag, completely blocking any network lookup.

### Component D: CI/CD Workflow (`ci-cd.yml`)
* **Role**: Automates testing, sync, obfuscation, and deployment.
* **Operation**: Manages dependencies on GitHub's cloud runners by leveraging Actions Caching to retain local wheel packages across runs, running the sync script dynamically to pull updates, and building the production container under 100% offline conditions.

---

## 3. Workflow Scenarios

### Scenario A: Adding a New Package Requirement (Dependency Updates)
When a developer adds a new package (or updates a version) in the requirements:
1. The **Dependency Sync** runs and compares the requirements list with the cached files.
2. It detects the new requirement is missing from the cache, contacts public PyPI to fetch the wheel (and its transient dependencies), and saves them to the host cache directory.
3. Because the directory is mounted as a Docker volume, the local PyPI container immediately starts serving the new package.
4. The Docker build is triggered and successfully consumes the new package from the local PyPI server.

### Scenario B: Local Testing with Dockerized PyPI Server
1. The developer builds the Docker image locally.
2. They supply the build argument pointing to the private PyPI server index running on the host machine (`host.docker.internal`).
3. Inside the build container, `pip` queries the host's private PyPI server to resolve and install the requirements.
4. **Isolation Proof**: If the developer points `pip` to a bogus local port, the build fails immediately on the first package download, proving that it never attempts to communicate with the public internet.

### Scenario C: Pure Local Directory Build (Zero Network Index)
For systems that require absolute zero-network configuration:
1. The developer copies the package cache directory directly into the Docker build context.
2. They trigger the build with an argument instructing the builder to use the local directory.
3. The Dockerfile executes the package installation using the `--no-index` and `--find-links` parameters.
4. `pip` resolves and installs all requirements directly from the copied folder, requiring no network connection whatsoever.

### Scenario D: GitHub Actions Push/PR Trigger (100% Offline CI)
When a push or pull request is made to the repository:
1. The GitHub Actions runner wakes up and restores the cached wheel directory from previous runs.
2. The sync script executes inside the runner, downloads only the diff (if any new packages were added), and updates the runner's cache.
3. The workflow builds the Docker image in **100% Offline Mode**. It sets the index URL to empty and tells the Dockerfile to use the local folder inside the build context.
4. The image builds completely offline, utilizing only the cached wheels, and is securely pushed to Docker Hub.

### Scenario E: GitHub Actions Manual Dispatch (Hybrid Tunnel CI)
When a developer manually triggers the workflow from the GitHub UI:
1. The developer has the option to provide a secure tunnel URL (such as an ngrok, Tailscale, or corporate VPN endpoint) leading to their private PyPI server.
2. The workflow configures the Docker build arguments to use this remote tunnel URL as the PyPI index.
3. The image builds securely, pulling packages directly from the developer's private server over the encrypted tunnel, providing a flexible and secure hybrid deployment pipeline.

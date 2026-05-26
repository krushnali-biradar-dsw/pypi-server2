#!/usr/bin/env python3
"""
GitHub Actions Helper: Get Next Tag Version.
Queries Docker Hub or GHCR for the latest tag and increments the patch version.
"""

import os
import sys
import requests

def get_latest_tag(repo_owner, repo_name):
    # Try fetching from GitHub Container Registry (GHCR)
    url = f"https://api.github.com/orgs/{repo_owner}/packages/container/{repo_name}/versions"
    user_url = f"https://api.github.com/users/{repo_owner}/packages/container/{repo_name}/versions"
    
    headers = {
        "Accept": "application/vnd.github+json"
    }
    # Add token if available in GHA
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            response = requests.get(user_url, headers=headers, timeout=10)
            
        if response.status_code == 200:
            versions = response.json()
            tags = []
            for v in versions:
                metadata = v.get("metadata", {})
                container = metadata.get("container", {})
                t_list = container.get("tags", [])
                tags.extend(t_list)
                
            valid_tags = []
            for t in tags:
                if t == "latest":
                    continue
                # Match semantic version format (e.g. 1.2.3)
                parts = t.split(".")
                if len(parts) == 3 and all(x.isdigit() for x in parts):
                    valid_tags.append(t)
                    
            if valid_tags:
                def semver_key(tag):
                    return [int(x) for x in tag.split(".")]
                valid_tags.sort(key=semver_key)
                return valid_tags[-1]
    except Exception as e:
        print(f"Error fetching GHCR tags: {e}", file=sys.stderr)
        
    # Docker Hub Fallback if configured or desired
    docker_image = os.environ.get("DOCKER_IMAGE_NAME") # e.g. "username/repo"
    if docker_image:
        url = f"https://registry.hub.docker.com/v2/repositories/{docker_image}/tags"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                results = res.json().get('results', [])
                tags = [r['name'] for r in results if r['name'] != 'latest']
                valid_tags = []
                for t in tags:
                    parts = t.split(".")
                    if len(parts) == 3 and all(x.isdigit() for x in parts):
                        valid_tags.append(t)
                if valid_tags:
                    def semver_key(tag):
                        return [int(x) for x in tag.split(".")]
                    valid_tags.sort(key=semver_key)
                    return valid_tags[-1]
        except Exception as e:
            print(f"Error fetching Docker Hub tags: {e}", file=sys.stderr)
            
    return "1.0.0"

def increment_version(version_str):
    try:
        parts = version_str.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
    except Exception:
        pass
    return "1.0.1"

def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "username/repo")
    parts = repo.split("/")
    owner = parts[0]
    name = parts[1] if len(parts) > 1 else "py-server"
    
    latest = get_latest_tag(owner, name)
    next_ver = increment_version(latest)
    print(next_ver)

if __name__ == "__main__":
    main()

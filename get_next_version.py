#!/usr/bin/env python3
"""
GitHub Actions Helper: Get Next Tag Version.
Queries Docker Hub for the latest semantic tag and increments the patch version.
"""

import os
import sys
import requests

def get_latest_tag(image_name):
    # E.g. image_name = "username/repository-name"
    url = f"https://registry.hub.docker.com/v2/repositories/{image_name}/tags"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            results = response.json().get('results', [])
            tags = [r['name'] for r in results if r['name'] != 'latest']
            
            valid_tags = []
            for t in tags:
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
    # Construct Docker Hub image name
    username = os.environ.get("DOCKER_HUB_USERNAME")
    
    repo = os.environ.get("GITHUB_REPOSITORY", "username/py-server")
    repo_name = repo.split("/")[-1]
    
    if not username:
        print("Error: DOCKER_HUB_USERNAME env var not set.", file=sys.stderr)
        # Fallback to local library
        username = "library"
        
    image_name = f"{username}/{repo_name}"
    print(f"Checking latest tags for Docker Hub image: {image_name}", file=sys.stderr)
    
    latest = get_latest_tag(image_name)
    print(f"Latest semantic version found: {latest}", file=sys.stderr)
    
    next_ver = increment_version(latest)
    print(next_ver)

if __name__ == "__main__":
    main()

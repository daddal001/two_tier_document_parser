#!/usr/bin/env python3
"""Cross-platform Docker daemon check used by Makefile.

Runs `docker info` and exits with code 0 if the daemon responds.
If Docker is not available, prints a clear error to stderr and exits 1.
"""
import shutil
import subprocess
import sys

def main():
    docker = shutil.which("docker")
    if not docker:
        print("Error: `docker` binary not found in PATH. Install Docker and ensure it's on your PATH.", file=sys.stderr)
        return 1
    try:
        subprocess.run([docker, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("Error: Docker does not appear to be running. Start Docker Desktop (Windows) or the Docker daemon and try again.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error checking Docker: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

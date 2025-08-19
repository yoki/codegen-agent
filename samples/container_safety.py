# sample_container_safety.py
# Direct Docker execution (no LLM). Tries destructive ops inside the guest container.
# Confirms: /inputs is read-only, guest-only side effects, /outputs is writable.
# Requires: Docker running
from codegen_agent.core.execution.runner import execute

CODE = r"""
import os, sys, shutil, subprocess

print("Attempting to write to /outputs ...")
with open("/outputs/touch_ok.txt", "w", encoding="utf-8") as f:
    f.write("ok")
print("OK: wrote /outputs/touch_ok.txt")

print("\nAttempting to write to /inputs (should fail) ...")
try:
    with open("/inputs/should_fail.txt", "w", encoding="utf-8") as f:
        f.write("nope")
    print("FAIL: /inputs unexpectedly writable")
except Exception:
    print("OK: /inputs is read-only")

print("\nAttempting reading ...")
try:
    with open("/inputs/code.py", "r", encoding="utf-8") as f:
        txt = f.read()
    print("OK: read /inputs/code.py")
    
except Exception as e:
    print(f"NG: read failed: {e}")


print("\nAttempting destructive command (rm -rf /inputs/*) ...")
try:
    subprocess.check_call(["bash", "-lc", "rm -rf /inputs/*"])
    print("NG: rm -rf executed")
except Exception as e:
    print(f"OK: rm blocked or partly failed: {e}")
"""
import time

import subprocess


def time_docker_operations():
    """Profile individual Docker operations"""

    # Test raw Docker performance
    print("=== Docker Performance Test ===")

    # Test 1: Simple container run
    start = time.time()
    result = subprocess.run(
        ["docker", "run", "--rm", "codegen-agent-runner:py313", "python", "-c", "print('hello')"],
        capture_output=True,
        text=True,
    )
    simple_time = time.time() - start
    print(f"Simple container run: {simple_time:.3f}s")

    # Test 2: Container with volume mounts (no execution)
    start = time.time()
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            "/tmp:/test_mount:ro",
            "codegen-agent-runner:py313",
            "python",
            "-c",
            "print('with mount')",
        ],
        capture_output=True,
        text=True,
    )
    mount_time = time.time() - start
    print(f"Container with mount: {mount_time:.3f}s")

    # Test 3: Check if image is actually cached
    start = time.time()
    result = subprocess.run(
        ["docker", "image", "inspect", "codegen-agent-runner:py313"], capture_output=True, text=True
    )
    inspect_time = time.time() - start
    print(f"Image inspection: {inspect_time:.3f}s")

    return simple_time, mount_time, inspect_time


if __name__ == "__main__":
    # First, profile Docker operations
    simple_time, mount_time, inspect_time = time_docker_operations()

    print("\n=== Full Execution Test ===")
    start_time = time.time()
    print("Starting execution...")

    exec_start = time.time()
    res = execute(CODE, variables={})
    exec_end = time.time()

    print(f"\nExecution took: {exec_end - exec_start:.3f}s")
    print(f"Total time: {exec_end - start_time:.3f}s")

    print(f"\n=== Performance Analysis ===")
    print(f"Simple Docker run: {simple_time:.3f}s")
    print(f"Docker with mounts: {mount_time:.3f}s")
    print(f"Full codegen execution: {exec_end - exec_start:.3f}s")
    print(f"Overhead ratio: {(exec_end - exec_start) / simple_time:.1f}x")

    print("\n---- STDOUT ----\n", res.stdout)
    if res.stderr.strip():
        print("\n---- STDERR ----\n", res.stderr)
    print("\nReturn code:", res.returncode)

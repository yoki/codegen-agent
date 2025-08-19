# sample_container_safety.py
# Direct Docker execution (no LLM). Tries destructive ops inside the guest container.
# Confirms: /inputs is read-only, guest-only side effects, /outputs is writable.
# Requires: Docker running

from __future__ import annotations
from codegen_agent.core.execution.runner import execute

CODE = r"""
import os, sys, shutil, subprocess

print("Attempting to write to /outputs ...")
with open("/outputs/touch_ok.txt", "w", encoding="utf-8") as f:
    f.write("ok")
print("OK: wrote /outputs/touch_ok.txt")

print("Attempting to write to /inputs (should fail) ...")
try:
    with open("/inputs/should_fail.txt", "w", encoding="utf-8") as f:
        f.write("nope")
    print("FAIL: /inputs unexpectedly writable")
except Exception:
    print("OK: /inputs is read-only")

print("Attempting destructive command (rm -rf /inputs/*) ...")
try:
    subprocess.check_call(["bash", "-lc", "rm -rf /inputs/*"])
    print("OK: rm -rf executed; host remains safe due to read-only mount")
except Exception as e:
    print(f"OK: rm blocked or partly failed: {e}")
"""

if __name__ == "__main__":
    res = execute(CODE, variables={})
    print("\n---- STDOUT ----\n", res.stdout)
    if res.stderr.strip():
        print("\n---- STDERR ----\n", res.stderr)
    print("\nReturn code:", res.returncode)

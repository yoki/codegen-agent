import subprocess

# import sys
from pathlib import Path
from typing import Optional


# class DockerRuntime:
#     """Minimal wrapper that ensures the runner image exists and executes a single run.

#     This uses the Docker CLI via subprocess for maximum portability and simplicity.
#     """

#     def __init__(self, image: str = "llm-analyze-runner:py313"):
#         self.image = image

#     def ensure_image(self, dockerfile: Optional[str] = None) -> None:
#         # Check if image exists
#         inspect = subprocess.run(["docker", "image", "inspect", self.image], capture_output=True)
#         if inspect.returncode == 0:
#             return

#         # Build if missing
#         if dockerfile is None:
#             # Resolve package-installed Dockerfile.runner
#             # Expect structure: <pkg_root>/sandbox/Dockerfile.runner
#             here = Path(__file__).resolve().parent.parent.parent  # llm_analyze/
#             dockerfile = str(here / "sandbox" / "Dockerfile.runner")
#         context_dir = str(Path(dockerfile).parent)
#         cmd = [
#             "docker",
#             "build",
#             "-t",
#             self.image,
#             "-f",
#             dockerfile,
#             context_dir,
#         ]
#         proc = subprocess.run(cmd, capture_output=True, text=True)

#         if proc.returncode != 0:
#             msg = [
#                 "Failed to build sandbox image.",
#                 f"Command: {' '.join(cmd)}",
#                 f"Return code: {proc.returncode}",
#                 f"STDOUT:\n{proc.stdout.strip()}",
#                 f"STDERR:\n{proc.stderr.strip()}",
#             ]
#             raise RuntimeError("\n".join(msg))

#     def run(self, inputs_dir: str, outputs_dir: str) -> subprocess.CompletedProcess:
#         cmd = [
#             "docker",
#             "run",
#             "--rm",
#             "-v",
#             f"{Path(inputs_dir).resolve()}:/inputs:ro",
#             "-v",
#             f"{Path(outputs_dir).resolve()}:/outputs:rw",
#             self.image,
#             "python",
#             "-u",
#             "/inputs/prelude.py",
#         ]
#         return subprocess.run(cmd, capture_output=True, text=True)


################################################
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# Minimal Dockerfile content kept in-code to avoid devcontainer/WSL path issues.
_DOCKERFILE_TEXT = """\
FROM python:3.13-slim

RUN pip install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    seaborn

ENV MPLCONFIGDIR=/tmp
WORKDIR /work
# Host will invoke: python -u /inputs/prelude.py
"""


class DockerRuntime:
    """
    Tiny wrapper around the Docker CLI (no SDK) that works from a devcontainer
    talking to a host daemon. Avoids relying on package paths for the build context
    by synthesizing a temporary context with an inline Dockerfile.
    """

    def __init__(self, image: Optional[str] = None):
        # You can prebuild/pull an image and set LLM_ANALYZE_RUNNER_IMAGE to skip builds.
        self.image = image or os.environ.get("LLM_ANALYZE_RUNNER_IMAGE", "llm-analyze-runner:py313")

    @staticmethod
    def _run(cmd: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, input=input_bytes, capture_output=True, text=True)

    def ensure_image(self, dockerfile: Optional[str] = None) -> None:
        # Fast path: image already present.
        insp = self._run(["docker", "image", "inspect", self.image])
        if insp.returncode == 0:
            return

        # Build if missing.
        if dockerfile is not None:
            df_path = Path(dockerfile)
            context_dir = str(df_path.parent)
            cmd = ["docker", "build", "-t", self.image, "-f", str(df_path), context_dir]
            proc = self._run(cmd)
            if proc.returncode != 0:
                msg = [
                    "Failed to build sandbox image (explicit dockerfile).",
                    f"Command: {' '.join(cmd)}",
                    f"Return code: {proc.returncode}",
                    f"STDOUT:\n{proc.stdout.strip()}",
                    f"STDERR:\n{proc.stderr.strip()}",
                ]
                raise RuntimeError("\n".join(msg))
            return

        # No path provided: synthesize a temp context with an inline Dockerfile.
        with tempfile.TemporaryDirectory(prefix="llm_analyze_build_") as ctx:
            ctx_path = Path(ctx)
            df = ctx_path / "Dockerfile"
            df.write_text(_DOCKERFILE_TEXT, encoding="utf-8")

            cmd = ["docker", "build", "-t", self.image, str(ctx_path)]
            proc = self._run(cmd)
            if proc.returncode != 0:
                msg = [
                    "Failed to build sandbox image (temp context).",
                    f"Context: {ctx_path}",
                    f"Command: {' '.join(cmd)}",
                    f"Return code: {proc.returncode}",
                    f"STDOUT:\n{proc.stdout.strip()}",
                    f"STDERR:\n{proc.stderr.strip()}",
                    "Hints:",
                    "  - If building inside a devcontainer, ensure the Docker CLI can reach the host Docker daemon.",
                    "  - Pre-build or pull an image and set LLM_ANALYZE_RUNNER_IMAGE to skip builds.",
                ]
                raise RuntimeError("\n".join(msg))

    def run(self, inputs_dir: str, outputs_dir: str) -> subprocess.CompletedProcess:
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{Path(inputs_dir).resolve()}:/inputs:ro",
            "-v",
            f"{Path(outputs_dir).resolve()}:/outputs:rw",
            self.image,
            "python",
            "-u",
            "/inputs/prelude.py",
        ]
        proc = self._run(cmd)
        # Some Docker errors appear only on stdout; surface both if needed.
        if proc.returncode != 0 and not proc.stderr:
            proc.stderr = proc.stdout
        return proc

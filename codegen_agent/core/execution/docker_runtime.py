import subprocess

# import sys
from pathlib import Path
from typing import Optional


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
    seaborn \
    scikit-learn \
    scipy \
    statsmodels \
    openpyxl 

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
        # You can prebuild/pull an image and set CODEGEN_AGENT_RUNNER_IMAGE to skip builds.
        self.image = image or os.environ.get("CODEGEN_AGENT_RUNNER_IMAGE", "codegen-agent-runner:py313")

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
        with tempfile.TemporaryDirectory(prefix="codegen_agent_build_") as ctx:
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
                    "  - Pre-build or pull an image and set codegen_agent_RUNNER_IMAGE to skip builds.",
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

import subprocess
import os
from pathlib import Path
from typing import Optional

from ..mypath_and_key import GEN_CODES_PATH


class DockerRuntime:
    """
    Docker runtime that uses an external Dockerfile for building the sandbox image.
    """

    def __init__(self, image: Optional[str] = None):
        # You can prebuild/pull an image and set CODEGEN_AGENT_RUNNER_IMAGE to skip builds.
        self.image = image or os.environ.get("CODEGEN_AGENT_RUNNER_IMAGE", "codegen-agent-runner:py313")

    @staticmethod
    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True)

    def ensure_docker(self) -> None:
        subprocess.run("start-docker")

    def ensure_image(self, dockerfile: Optional[str] = None) -> None:
        self.ensure_docker()
        # Fast path: image already present.
        insp = self._run(["docker", "image", "inspect", self.image])
        if insp.returncode == 0:
            # print(f"Docker image '{self.image}' already exists, using cached version")
            return

        print(f"Docker image '{self.image}' not found, building...")

        # Use the external Dockerfile.runner by default
        if dockerfile is None:
            dockerfile = "/workspaces/codegen-agent/sandbox/Dockerfile.runner"

        df_path = Path(dockerfile)
        context_dir = str(df_path.parent)
        cmd = ["docker", "build", "-t", self.image, "-f", str(df_path), context_dir]
        proc = self._run(cmd)
        if proc.returncode != 0:
            msg = [
                "Failed to build sandbox image.",
                f"Command: {' '.join(cmd)}",
                f"Return code: {proc.returncode}",
                f"STDOUT:\n{proc.stdout.strip()}",
                f"STDERR:\n{proc.stderr.strip()}",
            ]
            raise RuntimeError("\n".join(msg))
        print(f"Successfully built image '{self.image}' from {dockerfile}")

    def run(self, inputs_dir: str, outputs_dir: str) -> subprocess.CompletedProcess:
        self.ensure_docker()

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

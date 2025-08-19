import subprocess
import sys
from pathlib import Path
from typing import Optional


class DockerRuntime:
    """Minimal wrapper that ensures the runner image exists and executes a single run.

    This uses the Docker CLI via subprocess for maximum portability and simplicity.
    """

    def __init__(self, image: str = "llm-analyze-runner:py313"):
        self.image = image

    def ensure_image(self, dockerfile: Optional[str] = None) -> None:
        # Check if image exists
        inspect = subprocess.run(["docker", "image", "inspect", self.image], capture_output=True)
        if inspect.returncode == 0:
            return

        # Build if missing
        if dockerfile is None:
            # Resolve package-installed Dockerfile.runner
            # Expect structure: <pkg_root>/sandbox/Dockerfile.runner
            here = Path(__file__).resolve().parent.parent.parent  # llm_analyze/
            dockerfile = str(here / "sandbox" / "Dockerfile.runner")
        context_dir = str(Path(dockerfile).parent)
        cmd = [
            "docker",
            "build",
            "-t",
            self.image,
            "-f",
            dockerfile,
            context_dir,
        ]
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            raise RuntimeError("Failed to build sandbox image")

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
        return subprocess.run(cmd, capture_output=True, text=True)

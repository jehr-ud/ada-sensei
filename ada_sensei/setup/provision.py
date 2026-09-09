from __future__ import annotations

import json
import platform
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ..config import Config
from ..tools.subprocess import SubprocessRunner

STATE_FILE = "provisioning.json"


@dataclass
class ProvisionResult:
    server_available: bool
    model_available: bool
    installed: bool
    pulled: bool
    error: str | None = None

    @property
    def ok(self) -> bool:
        return not self.error and self.model_available


class DefaultModelProvisioner:
    def __init__(
        self,
        config: Config,
        *,
        runner: SubprocessRunner | None = None,
        cache_dir: str | Path | None = None,
        env: dict | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or SubprocessRunner(timeout_seconds=120)
        self.cache_dir = Path(
            cache_dir or (config.cache_dir or Path("/tmp/ada-sensei-cache"))
        )
        self.model = config.llm.model
        self._origin = self._origin_from(config.llm.base_url)
        self._env = env

    @staticmethod
    def _origin_from(base_url: str) -> str:
        parts = urlsplit(base_url)
        return f"{parts.scheme}://{parts.netloc}"

    def _state_path(self) -> Path:
        return self.cache_dir / STATE_FILE

    def _read_state(self) -> dict:
        path = self._state_path()
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (ValueError, OSError):
                return {}
        return {}

    def _write_state(self, result: ProvisionResult) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        state = {**asdict(result), "model": self.model, "ok": result.ok}
        self._state_path().write_text(json.dumps(state))

    def server_available(self, timeout: float = 2.0) -> bool:
        try:
            urllib.request.urlopen(f"{self._origin}/api/tags", timeout=timeout)
            return True
        except Exception:
            return False

    def model_available(self, timeout: float = 2.0) -> bool:
        try:
            with urllib.request.urlopen(
                f"{self._origin}/api/tags", timeout=timeout
            ) as response:
                data = json.loads(response.read())
            return any(
                m.get("name", "").split(":")[0]
                in {self.model, self.model.split(":")[0]}
                for m in data.get("models", [])
            )
        except Exception:
            return False

    def provision_if_needed(
        self, *, force: bool = False, dry_run: bool = False
    ) -> ProvisionResult:
        if not force:
            record = self._read_state()
            if record.get("ok"):
                return ProvisionResult(
                    server_available=bool(record.get("server_available")),
                    model_available=bool(record.get("model_available")),
                    installed=bool(record.get("installed")),
                    pulled=bool(record.get("pulled")),
                )

        server = self.server_available()
        installed = False
        if not server and not dry_run:
            error = self._install_ollama()
            if error:
                result = ProvisionResult(
                    server_available=False,
                    model_available=False,
                    installed=False,
                    pulled=False,
                    error=error,
                )
                self._write_state(result)
                return result
            installed = True
            server = self.server_available()

        pulled = False
        if server:
            if not self.model_available() and not dry_run:
                self.runner.run(["ollama", "pull", self.model])
                pulled = self.model_available()
            else:
                pulled = True
        result = ProvisionResult(
            server_available=server,
            model_available=pulled or (server and self.model_available()),
            installed=installed,
            pulled=pulled,
            error=(
                None
                if (server and self.model_available())
                else "default LLM could not be provisioned"
            ),
        )
        if not dry_run:
            self._write_state(result)
        return result

    def _install_ollama(self) -> str | None:
        system = platform.system().lower()
        if system == "darwin":
            if not self._which("brew"):
                return "Ollama installation requires Homebrew, which is not installed"
            result = self.runner.run(["brew", "install", "ollama"])
            if result.status != "pass":
                return "failed to install Ollama via Homebrew"
            self.runner.run(["brew", "services", "start", "ollama"])
            return None
        if system == "linux":
            result = self.runner.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]
            )
            _ = result
            return None
        return f"unsupported platform for automatic Ollama install: {system}"

    def _which(self, name: str) -> bool:
        import shutil

        return (
            shutil.which(name, path=self._env.get("PATH") if self._env else None)
            is not None
        )

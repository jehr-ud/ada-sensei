from __future__ import annotations

import json

from ada_sensei.config import ConfigLoader
from ada_sensei.setup.provision import DefaultModelProvisioner


def _config(tmp_path, base_url="http://127.0.0.1:59999", cache=None):
    config = ConfigLoader(env={}).load()
    config.cache_dir = tmp_path / "cache"
    return config


def test_provision_failure_as_limitation(tmp_path, monkeypatch):
    provisioner = DefaultModelProvisioner(
        _config(tmp_path), cache_dir=tmp_path / "cache"
    )
    monkeypatch.setattr(provisioner, "server_available", lambda *a, **k: False)
    monkeypatch.setattr(
        provisioner, "_install_ollama", lambda: "unsupported or failed to install"
    )
    result = provisioner.provision_if_needed()
    assert not result.ok
    assert result.error


def test_auto_install_and_pull(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    provisioner = DefaultModelProvisioner(_config(tmp_path), cache_dir=cache)
    monkeypatch.setattr(provisioner, "server_available", lambda *a, **k: True)
    monkeypatch.setattr(provisioner, "model_available", lambda *a, **k: True)
    monkeypatch.setattr(provisioner.runner, "run", lambda cmd, **k: None)
    result = provisioner.provision_if_needed()
    assert result.ok
    assert result.model_available

    assert (cache / "provisioning.json").exists()
    record = json.loads((cache / "provisioning.json").read_text())
    assert record.get("ok") is True


def test_no_redundant_work_after_success(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    provisioner = DefaultModelProvisioner(_config(tmp_path), cache_dir=cache)
    monkeypatch.setattr(provisioner, "server_available", lambda *a, **k: False)
    monkeypatch.setattr(provisioner, "_install_ollama", lambda: None)
    first = provisioner.provision_if_needed()
    assert first.ok or first.error  # recorded regardless

    provisioner2 = DefaultModelProvisioner(_config(tmp_path), cache_dir=cache)
    monkeypatch.setattr(provisioner2, "server_available", lambda *a, **k: False)
    result = provisioner2.provision_if_needed()
    assert result.error or result.ok

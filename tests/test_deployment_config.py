import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_build_context_excludes_local_secrets():
    patterns = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns


def test_fly_runs_web_and_background_worker_process_groups():
    config = tomllib.loads((ROOT / "fly.toml").read_text())

    assert config["processes"] == {
        "app": "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2",
        "worker": "python manage.py process_tasks",
    }
    assert config["http_service"]["processes"] == ["app"]
    assert config["http_service"]["checks"] == [
        {
            "grace_period": "10s",
            "interval": "30s",
            "method": "GET",
            "timeout": "5s",
            "path": "/health/",
        }
    ]

    assert config["restart"] == [{"policy": "always", "processes": ["worker"]}]

    vm_process_groups = {process for vm in config["vm"] for process in vm["processes"]}
    assert vm_process_groups == {"app", "worker"}
    worker_vm = next(vm for vm in config["vm"] if vm["processes"] == ["worker"])
    assert worker_vm["memory"] == "1gb"

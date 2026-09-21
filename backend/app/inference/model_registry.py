import os
from typing import Any, Dict


# ============================================================
# MODEL WORKER REGISTRY
# ============================================================
# IMPORTANT:
# FastAPI does NOT load any ML model here.
# This file stores worker configuration and launch metadata
# used by the Worker Lifecycle Manager.
# ============================================================

MODEL_WORKERS: Dict[str, Dict[str, Any]] = {
    "plane": {
        "port": 8100,
        "url": "http://127.0.0.1:8100",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.plane.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "spine": {
        "port": 8101,
        "url": "http://127.0.0.1:8101",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.spine.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "brain": {
        "port": 8102,
        "url": "http://127.0.0.1:8102",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.brain.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "lung": {
        "port": 8103,
        "url": "http://127.0.0.1:8103",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.lung.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "abdomen": {
        "port": 8104,
        "url": "http://127.0.0.1:8104",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.abdomen.worker:app",
        "disabled": True,
        "disabled_reason": "model unavailable",
    },
    "bone": {
        "port": 8105,
        "url": "http://127.0.0.1:8105",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.bone.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "placenta": {
        "port": 8106,
        "url": "http://127.0.0.1:8106",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.placenta.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "face": {
        "port": 8107,
        "url": "http://127.0.0.1:8107",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.11"],
        "module": "app.workers.face.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "heart": {
        "port": 8108,
        "url": "http://127.0.0.1:8108",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.heart.worker:app",
        "disabled": False,
        "disabled_reason": None,
    },
    "kidney": {
        "port": 8109,
        "url": "http://127.0.0.1:8109",
        "endpoint": "/predict",
        "python_cmd": ["py", "-3.10"],
        "module": "app.workers.kidney.worker:app",
        "disabled": True,
        "disabled_reason": "model unavailable",
    },
}


def get_worker_config(
    model_name: str,
) -> Dict[str, Any]:
    config = MODEL_WORKERS.get(model_name)
    if config is None:
        raise ValueError(f"Unknown model worker: {model_name}")
    env_url = os.getenv(f"WORKER_{model_name.upper()}_URL")
    if env_url:
        config = dict(config)
        config["url"] = env_url
    return config


def get_all_worker_configs() -> Dict[str, Dict[str, Any]]:
    resolved = {}
    for name, cfg in MODEL_WORKERS.items():
        env_url = os.getenv(f"WORKER_{name.upper()}_URL")
        if env_url:
            resolved[name] = dict(cfg, url=env_url)
        else:
            resolved[name] = cfg
    return resolved
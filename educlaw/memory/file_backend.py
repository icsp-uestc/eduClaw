from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import logging

from ..utils.logger import get_logger


class MemoryBackend(ABC):
    @abstractmethod
    def save(self, key: str, value: Any):
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        pass


class FileMemoryBackend(MemoryBackend):
    def __init__(self, base_path: str = "./data/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("memory.file", logging.INFO)

    def _get_file_path(self, key: str) -> Path:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        subdir = key_hash[:2]
        return self.base_path / subdir / f"{key_hash}.json"

    def save(self, key: str, value: Any):
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"key": key, "value": value, "timestamp": datetime.now().isoformat()}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, key: str) -> Optional[Any]:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data["value"]
        except Exception as e:
            self.logger.error(f"Failed to load {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        return self._get_file_path(key).exists()

    def list_keys(self, prefix: str = "") -> List[str]:
        keys = []
        for subdir in self.base_path.iterdir():
            if subdir.is_dir():
                for file_path in subdir.glob("*.json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if not prefix or data["key"].startswith(prefix):
                            keys.append(data["key"])
                    except Exception:
                        continue
        return keys

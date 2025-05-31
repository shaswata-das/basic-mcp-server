import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

class SecretsManager:
    """Simple secrets manager that loads secrets from a JSON file or environment."""

    def __init__(self, file_path: Optional[str] = None) -> None:
        self.secrets: Dict[str, Any] = {}
        if file_path:
            path = Path(file_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.secrets = json.load(f)
                except Exception:
                    # If secrets file is malformed, ignore but continue
                    self.secrets = {}

    def get(self, key: str, default: Any = None, rotate: bool = False) -> Any:
        """Retrieve a secret.

        Environment variables take precedence over file-based secrets.
        If ``rotate`` is True and the secret value is a list, the first
        value will be returned and moved to the end of the list.
        """
        env_val = os.environ.get(key)
        if env_val is not None:
            return env_val

        value = self.secrets.get(key, default)
        if rotate and isinstance(value, list) and value:
            current = value.pop(0)
            value.append(current)
            return current
        return value

_manager: Optional[SecretsManager] = None

def get_secrets_manager() -> SecretsManager:
    """Get a global :class:`SecretsManager` instance."""
    global _manager
    if _manager is None:
        file_path = os.environ.get("SECRETS_FILE")
        _manager = SecretsManager(file_path)
    return _manager

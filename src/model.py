from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import dataclass_json


class TooManyNodeWatchesException(Exception):
    pass


@dataclass_json
@dataclass
class NodeWatch:
    tg_chat_id: int
    ip: str
    api_port: int = 8080
    metrics_port: int = 9101
    seed_port: int = 6180
    is_ok: Optional[bool] = None
    modified: Optional[int] = 0
    checked: Optional[int] = 0
    errors: Optional[List[str]] = None
    alarm_sent: Optional[int] = 0

    def __str__(self) -> str:
        if self.is_ok is None:
            return f'❓ {self.ip} - Unknown status'
        if self.is_ok:
            return f'✅ {self.ip} - OK'
        return '\n'.join(f'❗{self.ip} - {error}' for error in self.errors)

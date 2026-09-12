from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import RigSnapshot


class HardwareError(RuntimeError):
    pass


class HardwareAdapter(ABC):
    @abstractmethod
    def snapshot(self) -> RigSnapshot:
        raise NotImplementedError

    @abstractmethod
    def set_valve(self, open_state: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def force_safe_state(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def output_is_safe(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

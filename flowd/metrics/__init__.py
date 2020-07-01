import abc
from typing import Tuple

CollectedData = Tuple[str, float]


class BaseCollector(abc.ABC):
    """Base class for metric collectors."""

    @property
    @abc.abstractmethod
    def metric_name(self) -> str:
        pass

    @abc.abstractmethod
    def stop_collect(self) -> None:
        pass

    @abc.abstractmethod
    def start_collect(self) -> None:
        pass

    @abc.abstractmethod
    def get_current_state(self) -> CollectedData:
        pass

    @abc.abstractmethod
    def cleanup(self) -> None:
        pass

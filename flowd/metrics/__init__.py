import abc


class BaseCollector(abc.ABC):
    """Base class for metric collectors."""

    @property
    @abc.abstractmethod
    def metric_name(self) -> str:
        pass

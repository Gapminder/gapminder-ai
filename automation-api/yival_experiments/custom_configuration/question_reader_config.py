from dataclasses import asdict, dataclass

from yival.data.base_reader import BaseReaderConfig


@dataclass
class QuestionReaderConfig(BaseReaderConfig):
    """
    Configuration specific to the questions reader.
    """

    def asdict(self):
        return asdict(self)

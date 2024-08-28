from dataclasses import asdict, dataclass
from typing import Any, Dict

from yival.schemas.evaluator_config import EvaluatorConfig, EvaluatorType


@dataclass
class SimpleEvaluatorConfig(EvaluatorConfig):
    evaluator_type: EvaluatorType = EvaluatorType.INDIVIDUAL
    description: str = "This is the description of the evaluator."
    scale_description: str = "0-4"

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

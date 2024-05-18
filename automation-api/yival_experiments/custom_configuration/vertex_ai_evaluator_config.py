from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

from yival.schemas.evaluator_config import EvaluatorConfig, EvaluatorType


@dataclass
class VertexAIEvaluatorConfig(EvaluatorConfig):
    evaluator_type: EvaluatorType = EvaluatorType.INDIVIDUAL
    prompt: Union[str, List[Dict[str, str]]] = ""
    choices: List[str] = field(default_factory=list)
    model_name: str = "vertex_ai/claude-3-opus@20240229"
    description: str = "This is the description of the evaluator."
    scale_description: str = "0-4"
    choice_scores: Optional[Dict[str, float]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

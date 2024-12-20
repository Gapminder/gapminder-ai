from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

from yival.schemas.evaluator_config import EvaluatorConfig, EvaluatorType


@dataclass
class ClaudeEvaluatorConfig(EvaluatorConfig):
    evaluator_type: EvaluatorType = EvaluatorType.INDIVIDUAL
    prompt: Union[str, List[Dict[str, str]]] = ""
    choices: List[str] = field(default_factory=list)
    model_name: str = "claude-3-5-sonnet-20241022"
    description: str = "This is an evaluator that uses Anthropic's Claude model."
    scale_description: str = "0-4"
    choice_scores: Optional[Dict[str, float]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from yival.schemas.varation_generator_configs import BaseVariationGeneratorConfig


@dataclass
class ModelConfigVariationGeneratorConfig(BaseVariationGeneratorConfig):
    models: Optional[List[Dict[str, Any]]] = None  # List of variations to generate

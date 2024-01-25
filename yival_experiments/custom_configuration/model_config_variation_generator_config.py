from dataclasses import dataclass
from yival.schemas.varation_generator_configs import BaseVariationGeneratorConfig

from typing import Optional, List, Dict, Any


@dataclass
class ModelConfigVariationGeneratorConfig(BaseVariationGeneratorConfig):
    models: Optional[List[Dict[str, Any]]] = None  # List of variations to generate

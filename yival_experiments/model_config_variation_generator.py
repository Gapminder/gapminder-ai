from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, List, Optional

# from yival.schemas.experiment_config import WrapperVariation
# ^ this is not working for dict so I write my own version

from yival.variation_generators.base_variation_generator import BaseVariationGenerator

from model_config_variation_generator_config import ModelConfigVariationGeneratorConfig


@dataclass
class WrapperVariation:
    """
    Represents a variation within a wrapper.
    The value can be any type, but typical usages might include strings,
    numbers, configuration dictionaries, or even custom class configurations.
    """

    value_type: str  # e.g., "string", "int", "float", "ClassA", ...
    value: Any  # The actual value or parameters to initialize a value
    instantiated_value: Any = field(init=False)
    variation_id: Optional[str] = None

    def asdict(self):
        return asdict(self)

    def __post_init__(self):
        self.instantiated_value = self.instantiate()

    def instantiate(self) -> Any:
        """
        Returns an instantiated value based on value_type and params.
        """
        return self.value


class ModelConfigVariationGenerator(BaseVariationGenerator):
    def __init__(self, config: ModelConfigVariationGeneratorConfig):
        super().__init__(config)
        self.config = config

    def generate_variations(self) -> Iterator[List[WrapperVariation]]:
        if not self.config.models:
            yield []
        else:
            variations = [
                WrapperVariation(value_type="dict", value=var)
                for var in self.config.models
            ]
            yield variations

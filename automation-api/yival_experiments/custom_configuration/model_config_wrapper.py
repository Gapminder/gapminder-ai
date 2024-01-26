from typing import Any, Dict, Optional

from model_config_wrapper_config import ModelConfigWrapperConfig
from yival.experiment.experiment_runner import ExperimentState
from yival.wrappers.base_wrapper import BaseWrapper


class ModelConfigWrapper(BaseWrapper):
    """
    A wrapper for model configuration.

    Configuration is a dictionary contains 2 keys:

    - model_name: the name of model, which is a string
    - params: the configuration of model, which is a dictionary
    """

    default_config = ModelConfigWrapperConfig()

    def __init__(
        self,
        value: Dict[str, Any],
        name: str,
        config: Optional[ModelConfigWrapperConfig] = None,
        state: Optional[ExperimentState] = None,
    ) -> None:
        super().__init__(name, config, state)
        self._value = value

    def get_value(self) -> Dict[str, Any]:
        variation = self.get_variation()
        if variation is not None:
            return variation
        return self._value

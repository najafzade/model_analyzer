# Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .config_generator_interface import ConfigGeneratorInterface

from model_analyzer.triton.model.model_config import ModelConfig
import abc


class BaseModelConfigGenerator(ConfigGeneratorInterface):
    """ Base class for generating model configs """

    # Dict of parameters to apply on top of the default config to result
    # in the default config (none)
    #
    DEFAULT_PARAM_COMBO = {}

    def __init__(self, config, model, client):
        """
        Parameters
        ----------
        config: ModelAnalyzerConfig
        model: The model to generate ModelConfigs for
        client: TritonClient
        """
        self._client = client
        self._model_repository = config.model_repository
        self._base_model = model
        self._base_model_name = model.model_name()
        self._cpu_only = model.cpu_only()
        self._model_name_index = 0
        self._live = False
        self._last_results = []

    def is_done(self):
        """ Returns true if this generator is done generating configs """
        return self._live and self._done_walking()

    def next_config(self):
        """
        Returns
        -------
        ModelConfig
            The next ModelConfig generated by this class
        """
        self._live = True
        while True:
            config = self._get_next_model_config()
            yield (config)
            self._step()

    def set_last_results(self, measurements):
        """ 
        Given the results from the last ModelConfig, make decisions 
        about future configurations to generate

        Parameters
        ----------
        measurements: List of Measurements from the last run(s)
        """
        self._last_results = measurements

    @abc.abstractmethod
    def _done_walking(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _step(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _get_next_model_config(self):
        raise NotImplementedError

    def _get_model_variant_name(self, param_combo):
        if param_combo is self.DEFAULT_PARAM_COMBO:
            variant_name = f'{self._base_model_name}_config_default'
        else:
            variant_name = f'{self._base_model_name}_config_{self._model_name_index}'
            self._model_name_index += 1
        return variant_name

    def _make_remote_model_config(self):
        if not self._reload_model_disable:
            self._client.load_model(self._base_model_name)
        model_config = ModelConfig.create_from_triton_api(
            self._client, self._base_model_name, self._num_retries)
        if not self._reload_model_disable:
            self._client.unload_model(self._base_model_name)

        return model_config

    def _make_direct_mode_model_config(self, param_combo):
        """ 
        Given a base model config and a combination of parameters to change,
        apply the changes on top of the base and return the new model config
        """
        model_config_dict = self._get_base_model_config_dict()
        if param_combo is not None:
            for key, value in param_combo.items():
                if value is not None:
                    model_config_dict[key] = value

        model_config_dict['name'] = self._get_model_variant_name(param_combo)

        model_config = ModelConfig.create_from_dictionary(model_config_dict)
        return model_config

    def _get_base_model_config_dict(self):
        config = ModelConfig.create_from_file(
            f'{self._model_repository}/{self._base_model_name}')
        return config.get_config()

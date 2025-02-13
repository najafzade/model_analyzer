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
from model_analyzer.config.run.run_config import RunConfig
from model_analyzer.config.generate.model_run_config_generator import ModelRunConfigGenerator
from model_analyzer.model_analyzer_exceptions import TritonModelAnalyzerException


class RunConfigGenerator(ConfigGeneratorInterface):
    """
    Generates all RunConfigs to execute given a list of models
    """

    def __init__(self, config, models, client):
        """
        Parameters
        ----------
        config: ModelAnalyzerConfig
        
        models: List of ConfigModelProfileSpec
            The models to generate ModelRunConfigs for
            
        client: TritonClient
        """
        self._config = config
        self._models = models
        self._client = client

        self._triton_env = self._determine_triton_server_env(models)

        self._num_models = len(models)

        self._curr_model_run_configs = [None] * self._num_models
        self._curr_results = [[]] * self._num_models
        self._curr_generators = [None] * self._num_models

    def is_done(self):
        return    self._curr_generators[0] is not None \
              and all([gen.is_done() for gen in self._curr_generators])

    def set_last_results(self, measurements):
        self._update_results_for_all_generators(measurements)
        self._send_results_to_appropriate_generators()

    def next_config(self):
        """
        Returns
        -------
        RunConfig
            The next RunConfig generated by this class
        """

        yield from self._generate_subset(0)

    def _generate_subset(self, index):
        mrcg = ModelRunConfigGenerator(self._config, self._models[index],
                                       self._client)
        model_run_config_generator = mrcg.next_config()

        self._curr_generators[index] = mrcg

        while not mrcg.is_done():
            next_config = next(model_run_config_generator)
            self._curr_model_run_configs[index] = next_config

            if index == (len(self._models) - 1):
                yield (self._make_run_config())
            else:
                yield from self._generate_subset(index + 1)

    def _make_run_config(self):
        run_config = RunConfig(self._triton_env)
        for index in range(len(self._models)):
            run_config.add_model_run_config(self._curr_model_run_configs[index])
        return run_config

    def _update_results_for_all_generators(self, measurements):
        for index in range(self._num_models):
            self._curr_results[index].extend(measurements)

    def _send_results_to_appropriate_generators(self):
        # Starting from the leaf generator, pass in the results and check to see if
        # that generator is done. If it is, continue and pass the next generator their
        # queued up results, etc
        for index in reversed(range(self._num_models)):
            self._curr_generators[index].set_last_results(
                self._curr_results[index])
            self._curr_results[index] = []
            if not self._curr_generators[index].is_done():
                break

    def _determine_triton_server_env(self, models):

        triton_env = models[0].triton_server_environment()

        for model in models:
            if model.triton_server_environment() != triton_env:
                raise TritonModelAnalyzerException(
                    f"Mismatching triton server environments. The triton server environment must be the same for all models when run concurrently"
                )

        return triton_env

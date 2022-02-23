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

from .base_model_config_generator import BaseModelConfigGenerator


class AutomaticModelConfigGenerator(BaseModelConfigGenerator):
    """ Given a model, generates model configs in automatic search mode """

    def __init__(self, config, model, client):
        """
        Parameters
        ----------
        config: ModelAnalyzerConfig
        model: The model to generate ModelConfigs for
        client: TritonClient
        """
        super().__init__(config, model, client)

        self._max_instance_count = config.run_config_search_max_instance_count
        self._max_model_batch_size = config.run_config_search_max_model_batch_size
        self._min_model_batch_size = config.run_config_search_min_model_batch_size

        self._instance_kind = "KIND_GPU"
        if self._cpu_only:
            self._instance_kind = "KIND_CPU"

        # State machine counters
        # (will be properly initialized in start_state_machine())
        #
        self._curr_instance_count = 0
        self._curr_max_batch_size = 0

        # We return the default combo first before starting the state machine.
        # This flag tracks if we have done that and thus are in the state machine
        #
        self._state_machine_started = False

    def _done_walking(self):
        return self._done_walking_max_batch_size() \
           and self._done_walking_instance_count()

    def _step(self):
        if not self._state_machine_started:
            self._start_state_machine()
        else:
            self._step_state_machine()

    def _start_state_machine(self):
        self._state_machine_started = True
        self._curr_instance_count = 1
        self._curr_max_batch_size = self._min_model_batch_size

    def _step_state_machine(self):
        if self._done_walking_max_batch_size():
            self._reset_max_batch_size()
            self._step_instance_count()
        else:
            self._step_max_batch_size()

    def _step_max_batch_size(self):
        self._curr_max_batch_size *= 2

    def _step_instance_count(self):
        self._curr_instance_count += 1

    def _done_walking_max_batch_size(self):
        return self._max_batch_size_limit_reached() \
            or self._last_results_erroneous()

    def _done_walking_instance_count(self):
        return self._curr_instance_count >= self._max_instance_count

    def _max_batch_size_limit_reached(self):
        return self._curr_max_batch_size * 2 > self._max_model_batch_size

    def _last_results_erroneous(self):
        for result in self._last_results:
            for measurement in result:
                if measurement is None:
                    return True
        return False

    def _reset_max_batch_size(self):
        self._curr_max_batch_size = self._min_model_batch_size

    def _get_next_model_config(self):
        param_combo = self._get_curr_param_combo()
        model_config = self._make_direct_mode_model_config(param_combo)
        return model_config

    def _get_curr_param_combo(self):

        if not self._state_machine_started:
            return self.DEFAULT_PARAM_COMBO

        config = {
            'dynamic_batching': {},
            'max_batch_size':
                self._curr_max_batch_size,
            'instance_group': [{
                'count': self._curr_instance_count,
                'kind': self._instance_kind
            }]
        }

        return config

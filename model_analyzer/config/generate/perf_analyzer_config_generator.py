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
from .generator_utils import GeneratorUtils as utils

from model_analyzer.config.input.config_defaults import DEFAULT_MEASUREMENT_MODE
from model_analyzer.constants import THROUGHPUT_GAIN
from model_analyzer.perf_analyzer.perf_config import PerfAnalyzerConfig


class PerfAnalyzerConfigGenerator(ConfigGeneratorInterface):
    """ 
    Given Perf Analyzer configuration options, generates Perf Analyzer configs 
    
    All combinations are created at time 0, but it may return is_done==true 
    earlier depending on results that it receives
    """

    def __init__(self, cli_config, model_name, model_perf_analyzer_flags):
        """
        Parameters
        ----------
        cli_config: ConfigCommandProfile
            CLI Configuration Options
            
        model_name: str
            Name of the model
        """
        self._curr_config_index = 0
        self._last_results = ["valid"]
        self._all_results = []

        self._model_name = model_name
        self._perf_analyzer_flags = model_perf_analyzer_flags

        self._batch_sizes = cli_config.batch_sizes
        self._concurrency = self._create_concurrency_list(cli_config)
        self._client_protocol_is_http = (cli_config.client_protocol == 'http')
        self._launch_mode_is_c_api = (cli_config.triton_launch_mode == 'c_api')
        self._triton_install_path = cli_config.triton_install_path
        self._output_model_repo_path = cli_config.output_model_repository_path
        self._protocol = cli_config.client_protocol
        self._triton_http_endpoint = cli_config.triton_http_endpoint
        self._triton_grpc_endpoint = cli_config.triton_grpc_endpoint
        self._client_protocol = cli_config.client_protocol

        self._generate_perf_configs()

    def is_done(self):
        """ Returns true if this generator is done generating configs """
        return self._all_configs_returned() or self._last_results_erroneous(
        ) or not self._throughput_gain_valid()

    def next_config(self):
        """ Returns the next generated config """
        config = self._configs[self._curr_config_index]
        self._curr_config_index += 1
        return config

    def set_last_results(self, measurement):
        """ 
        Given the results from the last PerfAnalyzerConfig, make decisions 
        about future configurations to generate

        Parameters
        ----------
        measurement: Measurement from the last run
        """
        self._last_results = measurement
        self._all_results.extend(measurement)

    def _create_concurrency_list(self, cli_config):
        if cli_config.concurrency:
            return cli_config.concurrency
        elif cli_config.run_config_search_disable:
            return [1]
        else:
            return utils.generate_log2_list(
                cli_config.run_config_search_max_concurrency)

    def _generate_perf_configs(self):
        perf_config_params = self._create_perf_config_params()

        self._configs = []

        for params in utils.generate_parameter_combinations(perf_config_params):
            new_perf_config = PerfAnalyzerConfig()
            new_perf_config.update_config(params)
            # User provided flags can override the search parameters
            new_perf_config.update_config(self._perf_analyzer_flags)

            self._configs.append(new_perf_config)

    def _create_perf_config_params(self):
        perf_config_params = {
            'model-name': [self._model_name],
            'batch-size': self._batch_sizes,
            'concurrency-range': self._concurrency,
            'measurement-mode': [DEFAULT_MEASUREMENT_MODE]
        }

        if self._launch_mode_is_c_api:
            perf_config_params.update({
                'service-kind': ['triton_c_api'],
                'triton-server-directory': [self._triton_install_path],
                'model-repository': [self._output_model_repo_path]
            })
        else:
            perf_config_params.update({
                'protocol': [self._client_protocol],
                'url': [
                    self._triton_http_endpoint if self._client_protocol_is_http
                    else self._triton_grpc_endpoint
                ]
            })

        return perf_config_params

    def _all_configs_returned(self):
        return len(self._configs) == self._curr_config_index

    def _last_results_erroneous(self):
        return not self._last_results

    def _throughput_gain_valid(self):
        if len(self._all_results) < 4:
            return True

        return self._calculate_throughput_gain(1) > THROUGHPUT_GAIN or \
            self._calculate_throughput_gain(2) > THROUGHPUT_GAIN or \
            self._calculate_throughput_gain(3) > THROUGHPUT_GAIN

    def _calculate_throughput_gain(self, index):
        throughput_before = self._get_throughput(
            self._all_results[-(index + 1)])
        throughput_after = self._get_throughput(self._all_results[-index])
        gain = (throughput_after - throughput_before) / throughput_before
        return gain

    def _get_throughput(self, measurement):
        return measurement.get_metric_value('perf_throughput')

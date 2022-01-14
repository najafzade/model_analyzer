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

from model_analyzer.perf_analyzer.perf_config import PerfAnalyzerConfig
from model_analyzer.config.generate.perf_analyzer_config_generator import PerfAnalyzerConfigGenerator
from model_analyzer.config.input.config_command_profile \
     import ConfigCommandProfile
from model_analyzer.cli.cli import CLI
from .common import test_result_collector as trc
from .common.test_utils import convert_to_bytes
from .mocks.mock_config import MockConfig
from .mocks.mock_os import MockOSMethods
from model_analyzer.config.generate.generator_utils import GeneratorUtils as utils

from model_analyzer.config.input.config_defaults import \
    DEFAULT_BATCH_SIZES, DEFAULT_TRITON_LAUNCH_MODE, \
    DEFAULT_CLIENT_PROTOCOL, DEFAULT_TRITON_INSTALL_PATH, DEFAULT_OUTPUT_MODEL_REPOSITORY, \
    DEFAULT_TRITON_INSTALL_PATH, DEFAULT_OUTPUT_MODEL_REPOSITORY, \
    DEFAULT_TRITON_HTTP_ENDPOINT, DEFAULT_TRITON_GRPC_ENDPOINT, DEFAULT_MEASUREMENT_MODE, \
    DEFAULT_RUN_CONFIG_MAX_CONCURRENCY


class TestPerfAnalyzerConfigGenerator(trc.TestResultCollector):

    def test_default(self):
        """
        Test Default:  
            - No CLI options specified
        
        Default (1) value will be used for batch size
        and log2(DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)+1 configs 
        will be generated by the auto-search
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        concurrencies = utils.generate_log2_list(
            DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)
        expected_configs = [
            self._create_expected_config(concurrency=c) for c in concurrencies
        ]

        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs)

    def test_search_disabled(self):
        """ 
        Test Search Disabled: 
            - Run Config Search disabled
        
        Default (1) value will be used for batch size
        and concurrency will be set to 1
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        expected_configs = [self._create_expected_config()]

        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, '--run-config-search-disable')

    def test_c_api(self):
        """ 
        Test C_API: 
            - Launch mode is C_API
        
        Default (1) values will be used for batch size/concurrency 
        and only one config will be generated 
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        concurrencies = utils.generate_log2_list(
            DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)
        expected_configs = [
            self._create_expected_config(concurrency=c, launch_mode='c_api')
            for c in concurrencies
        ]

        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, '--triton-launch-mode=c_api')

    def test_http(self):
        """ 
        Test HTTP: 
            - Client protocol is HTTP
        
        Default (1) values will be used for batch size/concurrency 
        and only one config will be generated 
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        concurrencies = utils.generate_log2_list(
            DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)
        expected_configs = [
            self._create_expected_config(concurrency=c, client_protocol='http')
            for c in concurrencies
        ]

        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, '--client-protocol=http')

    def test_batch_size_search_disabled(self):
        """ 
        Test Batch Size Search Disabled: 
            - Schmoo batch sizes
            - Run Config Search disabled
        
        Batch sizes: 1,2,4
        Default (1) value will be used concurrency 
        and 3 configs will be generated 
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        batch_sizes = [1, 2, 4]
        expected_configs = [
            self._create_expected_config(batch_size=b) for b in batch_sizes
        ]

        pa_cli_args = ['-b 1,2,4', '--run-config-search-disable']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

    def test_batch_size_search_enabled(self):
        """ 
        Test Batch Size Search Enabled: 
            - Schmoo batch sizes
            - Run Config Search enabled
        
        Batch sizes: 1,2,4
        Concurrency: log2(DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)+1
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        batch_sizes = [1, 2, 4]
        concurrencies = utils.generate_log2_list(
            DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)
        expected_configs = [
            self._create_expected_config(batch_size=b, concurrency=c)
            for b in batch_sizes
            for c in concurrencies
        ]

        pa_cli_args = ['-b 1,2,4']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

    def test_concurrency(self):
        """ 
        Test Concurrency: 
            - Schmoo concurrency
            - Test with auto-search enabled & disabled
        
        Concurrency: 1-4
        Default (1) value will be used for batch size 
        and 4 configs will be generated 
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        concurrencies = [1, 2, 3, 4]
        expected_configs = [
            self._create_expected_config(concurrency=c) for c in concurrencies
        ]

        pa_cli_args = ['-c 1,2,3,4']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

        pa_cli_args = ['-c 1,2,3,4', '--run-config-search-disable']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

    def test_batch_size_and_concurrency(self):
        """
        Test Batch Size and Concurrency:
            - Schmoo batch sizes and concurrency
            - Run Config Search enabled & disabled

        Batch sizes: 1,2,4
        Concurrency: 1-4
        

        12 configs will be generated
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        batch_sizes = [1, 2, 4]
        concurrencies = [1, 2, 3, 4]

        expected_configs = [
            self._create_expected_config(batch_size=b, concurrency=c)
            for b in batch_sizes
            for c in concurrencies
        ]

        pa_cli_args = ['-b 1,2,4', '-c 1,2,3,4']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

        pa_cli_args = ['-b 1,2,4', '-c 1,2,3,4', '--run-config-search-disable']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

    def test_max_concurrency(self):
        """ 
        Test Max Concurrency: 
            - Change max concurrency to non-default value
        
        Max Concurrency: 16
        Default (1) value will be used for batch size 
        and 5 configs (log2(16)+1) will be generated 
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        concurrencies = utils.generate_log2_list(16)
        expected_configs = [
            self._create_expected_config(concurrency=c) for c in concurrencies
        ]

        pa_cli_args = ['--run-config-search-max-concurrency', '16']
        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs, pa_cli_args)

    def test_perf_analyzer_flags(self):
        """
        Test Perf Analyzer Flags:  
            - No CLI options specified
            - Percentile (PA flag) set in model's YAML
        
        Default (1) value will be used for batch size
        and log2(DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)+1 configs 
        will be generated by the auto-search
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model:
                    perf_analyzer_flags:
                        percentile: 96
            """)
        # yapf: enable

        concurrencies = utils.generate_log2_list(
            DEFAULT_RUN_CONFIG_MAX_CONCURRENCY)
        expected_configs = [
            self._create_expected_config(
                concurrency=c, perf_analyzer_flags={'percentile': '96'})
            for c in concurrencies
        ]

        self._run_and_test_perf_analyzer_config_generator(
            yaml_content, expected_configs)

    def _create_expected_config(self,
                                batch_size=DEFAULT_BATCH_SIZES,
                                concurrency=1,
                                launch_mode=DEFAULT_TRITON_LAUNCH_MODE,
                                client_protocol=DEFAULT_CLIENT_PROTOCOL,
                                perf_analyzer_flags=None):
        expected_config = PerfAnalyzerConfig()
        expected_config._options['-m'] = 'my-model'
        expected_config._options['-b'] = batch_size
        expected_config._args['concurrency-range'] = concurrency
        expected_config._args['measurement-mode'] = DEFAULT_MEASUREMENT_MODE

        expected_config.update_config(perf_analyzer_flags)

        if launch_mode == 'c_api':
            expected_config._args['service-kind'] = 'triton_c_api'
            expected_config._args[
                'triton-server-directory'] = DEFAULT_TRITON_INSTALL_PATH
            expected_config._args[
                'model-repository'] = DEFAULT_OUTPUT_MODEL_REPOSITORY
        else:
            expected_config._options['-i'] = client_protocol
            if client_protocol == 'http':
                expected_config._options['-u'] = DEFAULT_TRITON_HTTP_ENDPOINT
            else:
                expected_config._options['-u'] = DEFAULT_TRITON_GRPC_ENDPOINT

        return expected_config

    def _run_and_test_perf_analyzer_config_generator(self,
                                                     yaml_content,
                                                     expected_configs,
                                                     pa_cli_args=None):
        args = [
            'model-analyzer', 'profile', '--model-repository', 'cli_repository',
            '-f', 'path-to-config-file'
        ]

        if type(pa_cli_args) == list:
            args = args + pa_cli_args
        elif type(pa_cli_args) == str:
            args.append(pa_cli_args)

        config = self._evaluate_config(args, yaml_content)

        pacg = PerfAnalyzerConfigGenerator(
            config, config.profile_models[0].model_name(),
            config.profile_models[0].perf_analyzer_flags(),
            config.profile_models[0].parameters())

        perf_analyzer_configs = []
        while not pacg.is_done():
            perf_analyzer_configs.append(pacg.next_config())

        self.assertEqual(len(expected_configs), len(perf_analyzer_configs))
        for i in range(len(expected_configs)):
            self.assertEqual(expected_configs[i]._options['-m'],
                             perf_analyzer_configs[i]._options['-m'])
            self.assertEqual(expected_configs[i]._options['-b'],
                             perf_analyzer_configs[i]._options['-b'])
            self.assertEqual(expected_configs[i]._options['-i'],
                             perf_analyzer_configs[i]._options['-i'])
            self.assertEqual(expected_configs[i]._options['-u'],
                             perf_analyzer_configs[i]._options['-u'])

            self.assertEqual(
                expected_configs[i]._args['concurrency-range'],
                perf_analyzer_configs[i]._args['concurrency-range'])
            self.assertEqual(expected_configs[i]._args['measurement-mode'],
                             perf_analyzer_configs[i]._args['measurement-mode'])
            self.assertEqual(expected_configs[i]._args['service-kind'],
                             perf_analyzer_configs[i]._args['service-kind'])
            self.assertEqual(
                expected_configs[i]._args['triton-server-directory'],
                perf_analyzer_configs[i]._args['triton-server-directory'])
            self.assertEqual(expected_configs[i]._args['model-repository'],
                             perf_analyzer_configs[i]._args['model-repository'])

            # Future-proofing (in case a new field gets added)
            self.assertEqual(expected_configs[i]._options,
                             perf_analyzer_configs[i]._options)
            self.assertEqual(expected_configs[i]._args,
                             perf_analyzer_configs[i]._args)

    def _evaluate_config(self, args, yaml_content):
        mock_config = MockConfig(args, yaml_content)
        mock_config.start()
        config = ConfigCommandProfile()
        cli = CLI()
        cli.add_subcommand(
            cmd='profile',
            help=
            'Run model inference profiling based on specified CLI or config options.',
            config=config)
        cli.parse()
        mock_config.stop()
        return config

    def setUp(self):
        # Mock path validation
        self.mock_os = MockOSMethods(
            mock_paths=['model_analyzer.config.input.config_utils'])
        self.mock_os.start()

    def tearDown(self):
        self.mock_os.stop()

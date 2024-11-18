#!/usr/bin/env python3
'''starbench is an application that is able to measure the execution time of a user software suite in various conditions (different build modes and different execution modes)

'''
__version__ = '1.0.2'
import argparse
import json
import os
import pandas as pd
from typing import List, Optional
from pathlib import Path
from .core import CommandPerfEstimator, StopAfterSingleRun, FileTreeProviderCreatorRegistry, IFileTreeProvider, PasswordProviderFactory
from .passwordfile import LocalFilePPCreator
from .existingdir import ExistingDirCreator
from .gitcloner import GitClonerCreator


def starbench_cmake_app(source_code_provider: IFileTreeProvider, output_measurements_file_path: Path, tmp_dir: Path, num_cores: int, benchmark_command: List[str], cmake_options: Optional[List[str]] = None, cmake_exe_location: Path = None):
    """
    tests_to_run : regular expression as understood by ctest's -L option. eg '^arch4_quick$'
    """
    measurements = pd.DataFrame(columns=['worker_id', 'duration'])
    src_dir = source_code_provider.get_source_tree_path()
    # we need one build for each parallel run, otherwise running ctest on parallel would overwrite the same file, which causes the test to randomly fail depnding on race conditions
    worker_dir = tmp_dir / 'worker<worker_id>'
    build_dir = worker_dir / 'build'
    if cmake_options is None:
        cmake_options = []
    print(f'creating build directory {worker_dir}')
    create_build_dir = CommandPerfEstimator(
        run_command=['mkdir', '-p', str(build_dir)],
        num_cores_per_run=1,
        num_parallel_runs=num_cores,
        max_num_cores=num_cores,
        stop_condition=StopAfterSingleRun(),
        run_command_cwd=Path('/tmp'),
        stdout_filepath=worker_dir / 'createdir_stdout.txt',
        stderr_filepath=worker_dir / 'createdir_stderr.txt')
    _create_build_dir_duration = create_build_dir.run()  # noqa: F841
    # build_dir.mkdir(exist_ok=True)

    print(f'configuring {src_dir} into {build_dir} ...')
    cmake_prog = 'cmake'
    if cmake_exe_location:
        cmake_prog = str(cmake_exe_location)
    configure = CommandPerfEstimator(
        run_command=[cmake_prog] + cmake_options + [str(src_dir)],
        num_cores_per_run=1,
        num_parallel_runs=num_cores,
        max_num_cores=num_cores,
        stop_condition=StopAfterSingleRun(),
        run_command_cwd=build_dir,
        stdout_filepath=worker_dir / 'configure_stdout.txt',
        stderr_filepath=worker_dir / 'configure_stderr.txt')
    _configure_duration = configure.run()  # noqa: F841

    print(f'building {build_dir} ...')
    build = CommandPerfEstimator(
        run_command=['make'],
        num_cores_per_run=1,
        num_parallel_runs=num_cores,
        max_num_cores=num_cores,
        stop_condition=StopAfterSingleRun(),
        run_command_cwd=build_dir,
        stdout_filepath=worker_dir / 'build_stdout.txt',
        stderr_filepath=worker_dir / 'build_stderr.txt')
    _build_duration = build.run()  # noqa: F841

    print(f'benchmarking {build_dir} ...')
    stop_condition = StopAfterSingleRun()
    bench = CommandPerfEstimator(
        run_command=benchmark_command,
        num_cores_per_run=1,
        num_parallel_runs=num_cores,
        max_num_cores=num_cores,
        stop_condition=stop_condition,
        run_command_cwd=build_dir,
        stdout_filepath=worker_dir / 'bench_stdout.txt',
        stderr_filepath=worker_dir / 'bench_stderr.txt')
    mean_duration = bench.run()
    print(f'duration : {mean_duration:.3f} s' % ())
    measurements.loc[len(measurements)] = {'worker_id': '<average>', 'duration': mean_duration}
    measurements.to_csv(output_measurements_file_path, sep='\t')


def main():
    '''main program'''

    example_output_dir = Path('/tmp/hibench')
    example_src_dir = example_output_dir / 'source.git'
    example_password_provider = f'{{"type": "password-file", "password-file-path": "{os.getenv("HOME")}/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat"}}'
    example_source_tree_provider = f'{{"type": "git-cloner", "repos-url": "https://github.com/hibridon/hibridon", "src-dir": "{example_src_dir}", "code-version": "a3bed1c3ccfbca572003020d3e3d3b1ff3934fad", "git-user": "g-raffy", "password-provider": {example_password_provider}}}'
    example_text = f'''example:

    %(prog)s --source-tree-provider '{example_source_tree_provider}' --num-cores 2 --output-dir={example_output_dir} --cmake-path=/usr/bin/cmake --cmake-option=-DCMAKE_BUILD_TYPE=Release --cmake-option=-DBUILD_TESTING=ON --benchmark-command='ctest --output-on-failure -L ^arch4_quick$'

    '''

    pass_prov_fac = PasswordProviderFactory()
    pass_prov_fac.register_password_provider_creator(LocalFilePPCreator())

    tree_creator_factory = FileTreeProviderCreatorRegistry()
    tree_creator_factory.register_tree_creator_creator(GitClonerCreator())
    tree_creator_factory.register_tree_creator_creator(ExistingDirCreator())

    parser = argparse.ArgumentParser(description='performs a benchmark on a cmake buildable app hosted on a git repository', epilog=example_text, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source-tree-provider', type=str, required=True, help='the method to use to populate the source tree, in the form of a json string.')
    parser.add_argument('--num-cores', type=int, required=True, help='the number of cores that the benchmark will use')
    parser.add_argument('--output-dir', type=Path, required=True, help='where the output files will be placed')
    parser.add_argument('--cmake-path', type=Path, help='the path to the cmake executable to use in case a specific cmake is wanted')
    parser.add_argument('--cmake-option', type=str, action='append', help='additional option passed to cmake in the configure step (use this flag multiple times if you need more than one cmake option)')
    parser.add_argument('--benchmark-command', required=True, type=str, help='the command to benchmark')
    parser.add_argument('--output-measurements', type=Path, required=True, help='the path to the output tsv file containing the measurements table')
    args = parser.parse_args()

    # git_user = args.git_user
    # git_repos_url = args.git_repos_url

    # git_password = None
    # if args.git_pass:
    #     git_password = args.git_pass
    # elif args.git_pass_file:
    #     with open(args.git_pass_file, 'r', encoding='utf8') as f:
    #         git_password = f.readline().replace('\n', '')  # os.environ['HIBRIDON_REPOS_PAT']

    source_tree_provider_params = json.loads(args.source_tree_provider)

    source_tree_provider = tree_creator_factory.create_tree_creator(source_tree_provider_params['type'], source_tree_provider_params)
#    source_tree_provider = GitRepos(git_repos_url=git_repos_url, code_version=args.code_version, git_user=git_user, git_password=git_password, src_dir=args.output_dir / 'source.git')

    starbench_cmake_app(source_tree_provider, output_measurements_file_path=args.output_measurements, tmp_dir=args.output_dir, num_cores=args.num_cores, cmake_options=args.cmake_option, benchmark_command=args.benchmark_command.split(' '), cmake_exe_location=args.cmake_path)


if __name__ == '__main__':
    main()

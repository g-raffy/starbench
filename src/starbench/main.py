#!/usr/bin/env python3
'''starbench is an application that is able to measure the execution time of a user software suite in various conditions (different build modes and different execution modes)

'''
__version__ = '1.0.0'
import argparse
from abc import ABC, abstractmethod
import subprocess
from typing import List, Optional
from pathlib import Path
from .core import GitCommitId, Url, CommandPerfEstimator, StopAfterSingleRun


class IFileTreeProvider(ABC):

    @abstractmethod
    def get_source_tree_path(self) -> Path:
        pass


class ExistingDir(IFileTreeProvider):
    dir_path: Path

    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def get_source_tree_path(self) -> Path:
        return self.dir_path


class GitRepos(IFileTreeProvider):
    git_repos_url: Url
    git_user: Optional[str]
    git_password: Optional[str]
    code_version: Optional[GitCommitId]
    src_dir: Optional[Path]  # the temporary directory used to populate the source code

    def __init__(self, git_repos_url: Url, git_user: Optional[str] = None, git_password: Optional[str] = None, code_version: Optional[GitCommitId] = None, src_dir: Optional[Path] = None):
        self.git_repos_url = git_repos_url
        self.git_user = git_user
        self.git_password = git_password
        self.code_version = code_version
        self.src_dir = src_dir

    def get_source_tree_path(self) -> Path:
        self.src_dir.mkdir(exist_ok=True)
        git_credentials = []
        if self.git_user:
            git_credentials.append(self.git_user)
        if self.git_password:
            git_credentials.append(self.git_password)
        git_repos_url = self.git_repos_url
        if len(git_credentials) != 0:
            git_repos_url = git_repos_url.replace('https://', f"https://{':'.join(git_credentials)}@")
        # src_dir.mkdir(exist_ok=True)
        subprocess.run(['git', 'clone', f'{str(self.git_repos_url)}', str(self.src_dir)], cwd=str(self.src_dir), check=True)
        if self.code_version:
            subprocess.run(['git', 'checkout', f'{self.code_version}'], cwd=str(self.src_dir), check=True)
        return self.src_dir


def starbench_cmake_app(source_code_provider: IFileTreeProvider, tmp_dir: Path, num_cores: int, benchmark_command: List[str], cmake_options: Optional[List[str]] = None, cmake_exe_location: Path = None):
    """
    tests_to_run : regular expression as understood by ctest's -L option. eg '^arch4_quick$'
    """
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


def main():
    '''main program'''

    example_text = '''example:

    %(prog)s --git-repos-url https://github.com/hibridon/hibridon --code-version a3bed1c3ccfbca572003020d3e3d3b1ff3934fad --git-user g-raffy --git-pass-file "$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat" --num-cores 2 --output-dir=/tmp/hibench --cmake-path=/opt/cmake/cmake-3.23.0/bin/cmake --cmake-option=-DCMAKE_BUILD_TYPE=Release --cmake-option=-DBUILD_TESTING=ON --benchmark-command='ctest --output-on-failure -L ^arch4_quick$'

    '''

    parser = argparse.ArgumentParser(description='performs a benchmark on a cmake buildable app hosted on a git repository', epilog=example_text, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--git-repos-url', required=True, help='the url of the code to benchmark (eg https://github.com/hibridon/hibridon)')
    parser.add_argument('--code-version', help='the version of the code to use; either a branch or a commit id (eg a3bed1c3ccfbca572003020d3e3d3b1ff3934fad)')
    parser.add_argument('--git-user', help='the git user to use to clone the code repository')
    password_group = parser.add_mutually_exclusive_group()
    password_group.add_argument('--git-pass-file', help='the path to a file containing the password (or personal access token)')
    password_group.add_argument('--git-pass', type=str, help='the password (or personal access token) to use (not recommended for security reasons)')
    parser.add_argument('--num-cores', type=int, required=True, help='the number of cores that the benchmark will use')
    parser.add_argument('--output-dir', type=Path, required=True, help='where the output files will be placed')
    parser.add_argument('--cmake-path', type=Path, help='the path to the cmake executable to use in case a specific cmake is wanted')
    parser.add_argument('--cmake-option', type=str, action='append', help='additional option passed to cmake in the configure step (use this flag multiple times if you need more than one cmake option)')
    parser.add_argument('--benchmark-command', required=True, type=str, help='the command to benchmark')
    args = parser.parse_args()

    git_user = args.git_user
    git_repos_url = args.git_repos_url

    git_password = None
    if args.git_pass:
        git_password = args.git_pass
    elif args.git_pass_file:
        with open(args.git_pass_file, 'r', encoding='utf8') as f:
            git_password = f.readline().replace('\n', '')  # os.environ['HIBRIDON_REPOS_PAT']

    source_tree_provider = GitRepos(git_repos_url=git_repos_url, code_version=args.code_version, git_user=git_user, git_password=git_password, src_dir=args.output_dir / 'source.git')

    starbench_cmake_app(source_tree_provider, tmp_dir=args.output_dir, num_cores=args.num_cores, cmake_options=args.cmake_option, benchmark_command=args.benchmark_command.split(' '), cmake_exe_location=args.cmake_path)


if __name__ == '__main__':
    main()

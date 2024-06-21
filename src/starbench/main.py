#!/usr/bin/env python3
'''starbench is an application that is able to measure the execution time of a user software suite in various conditions (different build modes and different execution modes)

'''
__version__ = '1.0.0'
import argparse
import threading
import subprocess
import os
import sys
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
# from typing import ForwardRef
try:
    from typing import ForwardRef  # type: ignore pylint: disable=ungrouped-imports
except ImportError:
    # python 3.6
    from typing import _ForwardRef as ForwardRef

assert sys.version_info >= (3, 5, 0), 'this code requires at least python 3.5'  # type hints in arguments


class StarBenchException(Exception):
    '''base exception for user errors detected by starbench'''


RunId = int  # identifier of a run
WorkerId = int  # identifier of a worker (a run is performed on a worker)
DurationInSeconds = float
ProcessId = int
ReturnCode = int


class Run():
    """represents a run of a run of the benchmarked command within its CommandPerfEstimator
    """
    id: RunId  # uniquely identifies a run within its CommandPerfEstimator instance
    worker_id: WorkerId  # the worker used for this run (number of workers = number of parallel runs)
    pid: Optional[ProcessId]  # the process identifier of the process used by the command
    start_time: datetime  # the time at which the command process has started
    return_code: ReturnCode  # the exit code of the command process
    end_time: Optional[datetime]  # the time at which the command process has ended. None if the process is still running

    def __init__(self, run_id: RunId, worker_id: WorkerId):
        self.id = run_id
        self.worker_id = worker_id
        self.pid = None
        self.return_code = 0
        self.start_time = datetime.now()
        self.end_time = None

    def has_finished(self) -> bool:
        """indicates if this run has finished"""
        return self.end_time is not None

    def get_duration(self) -> DurationInSeconds:
        """returns the duration of this run, provided it has finished
        """
        assert self.has_finished()
        return (self.end_time - self.start_time).total_seconds()


CommandPerfEstimator = ForwardRef('CommandPerfEstimator')


class IStarBencherStopCondition(ABC):
    """abstract handler that decides if the given CommandPerfEstimator has enough runs to estimate the performance or should trigger new runs

    """
    @abstractmethod
    def should_stop(self, star_bencher: CommandPerfEstimator) -> bool:
        """decides if the given CommandPerfEstimator instance should trigger new runs

        This method is called at the end of each run, to decide if another run should be triggered or not.
        """


class StopAfterSingleRun(IStarBencherStopCondition):
    """a stop condition that causes the given CommandPerfEstimator to never start new runs

    as a result, this causes the given CommandPerfEstimator to just use one single run of the command to estimate its performance.
    """
    def __init__(self):
        pass

    def should_stop(self, star_bencher: CommandPerfEstimator):
        # never start a new run
        return True


class StopWhenConverged(IStarBencherStopCondition):
    """a stop condition that triggers when the just completed run doesn't have much effect on the average run's duration
    """
    def __init__(self, max_error: float = 0.01):
        self.max_error = max_error
        self._last_mean_duration = None

    def should_stop(self, star_bencher: CommandPerfEstimator) -> bool:
        do_stop = False
        mean_duration, _num_runs = star_bencher.get_run_mean_duration()
        print(f'mean_duration = {mean_duration}')
        if self._last_mean_duration is not None:
            diff = abs(mean_duration - self._last_mean_duration)
            print(f'diff = {diff}')
            if diff < self.max_error:
                do_stop = True
        self._last_mean_duration = mean_duration
        return do_stop


class CommandPerfEstimator():  # (false positive) pylint: disable=function-redefined
    '''a command runner that runs a given command multiple times and measures the average execution duration

    the 'star' term comes from hpl's stadgemm benchmark, where we launch `n` independent programs on `n` cores
    '''
    run_command: List[str]  # the command that this instance of CommandPerfEstimator is expected to run (eg: ['ctest', '--output-on-failure', '-L', '^arch4_quick$']). The command supports the following tags:
    run_command_cwd: Path  # the current directory to use when executing run_command
    stdout_filepath: Path  # the path of the file that records the standard output of run_command
    stderr_filepath: Path  # the path of the file that records the standard error of run_command
    num_cores_per_run: int  # the max number of threads used by each run
    num_parallel_runs: int  # how many times run_command is run simultaneously
    max_num_cores: int  # the maximum allowed number of cores for this CommandPerfEstimator
    stop_condition: IStarBencherStopCondition  # the condition that is used so that this CommandPerfEstimator can decide to stop launching commands
    stop_on_error: bool
    _next_run_id: int
    _runs: Dict[int, Run]
    _last_mean_duration: Optional[DurationInSeconds]
    _num_runs: int
    _runs_lock: threading.Lock
    _finished_event: threading.Event

    def __init__(self, run_command: List[str], num_cores_per_run: int, num_parallel_runs: int, max_num_cores: int, stop_condition: IStarBencherStopCondition, stop_on_error=True, run_command_cwd: Path = None, stdout_filepath: Path = None, stderr_filepath: Path = None):
        assert num_cores_per_run * num_parallel_runs <= max_num_cores
        self.run_command = run_command
        self.run_command_cwd = run_command_cwd
        self.stdout_filepath = stdout_filepath
        self.stderr_filepath = stderr_filepath
        self.num_cores_per_run = num_cores_per_run
        self.num_parallel_runs = num_parallel_runs
        self.max_num_cores = max_num_cores
        self.stop_condition = stop_condition
        self.stop_on_error = stop_on_error
        self._next_run_id = 0
        self._runs = {}
        self._last_mean_duration = None
        self._num_runs = 0
        self._runs_lock = threading.Lock()
        self._finished_event = threading.Event()

    def popen_and_call(self, popen_args: List[str], on_exit: Callable[[ProcessId, ReturnCode, RunId], None], run_id: RunId, cwd: Path, stdout_filepath: Path = None, stderr_filepath: Path = None):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        on_exit when the subprocess completes.
        on_exit is a callable object, and popen_args is a list/tuple of args that
        would give to subprocess.Popen.
        """
        def run_in_thread(popen_args: List[str], on_exit: Callable[[ProcessId, ReturnCode, RunId], None]):
            stdout = None
            stderr = None
            if stdout_filepath is not None:
                stdout = open(stdout_filepath, 'w', encoding='utf8')
            if stderr_filepath is not None:
                stderr = open(stderr_filepath, 'w', encoding='utf8')
            env = os.environ.copy()
            # restrict the number of threads used by openmp
            env['OMP_NUM_THREADS'] = f'{self.num_cores_per_run}'
            # restrict the nu,ber of threads used by intel math kernel library
            env['MKL_NUM_THREADS'] = f'{self.num_cores_per_run}'
            proc = subprocess.Popen(popen_args, cwd=cwd, stdout=stdout, stderr=stderr, env=env)
            proc.wait()
            if stderr is not None:
                stderr.close()
            if stdout is not None:
                stdout.close()
            on_exit(proc.pid, proc.returncode, run_id)
            return
        thread = threading.Thread(target=run_in_thread, args=(popen_args, on_exit))
        thread.start()
        # returns immediately after the thread starts
        return thread

    def get_run_mean_duration(self) -> Tuple[DurationInSeconds, int]:
        """returns the average duration of all completed runs of this CommandPerfEstimator instance
        """
        duration_sums = 0.0  # in python3.6+, replace with duration_sums: float = 0.0
        num_finished_runs = 0  # in python3.6+, replace with num_finished_runs: int = 0
        with self._runs_lock:
            for run in self._runs.values():
                if run.has_finished():
                    num_finished_runs += 1
                    duration_sums += run.get_duration()
        assert num_finished_runs > 0
        return duration_sums / num_finished_runs, num_finished_runs

    def _all_runs_have_finished(self):
        with self._runs_lock:
            for run in self._runs.values():
                if not run.has_finished():
                    return False
        return True

    def on_exit(self, pid: ProcessId, return_code: ReturnCode, run_id: RunId):
        """method called when the command executed by a run ends. Unless the stop condition is met, a new run is started.

        pid: the process identifier of the process of the run that just finished
        return_code: the return code of the process of the run that just finished
        run_id: the run that just completed
        """
        end_time = datetime.now()
        # print(self, pid, run_id)
        run = self._runs[run_id]
        run.pid = pid
        run.end_time = end_time
        run.return_code = return_code

        do_stop = False
        if self.stop_on_error and run.return_code != 0:
            do_stop = True
        else:
            do_stop = self.stop_condition.should_stop(self)
        if not do_stop:
            # print('adding a run')
            self._start_run(run.worker_id)  # reuse the same worker as the run that has just finished
        if self._all_runs_have_finished():
            # tell the main thread that all the runs have finished
            self._finished_event.set()

    @staticmethod
    def _interpret_tags(tagged_string: str, tags_value: Dict[str, str]) -> str:
        untagged_string = tagged_string
        for tag_id, tag_value in tags_value.items():
            untagged_string = untagged_string.replace(tag_id, tag_value)
        return untagged_string

    def _start_run(self, worker_id: WorkerId):
        """starts a run using the given worker"""
        tags_value = {
            '<worker_id>': f'{worker_id:03d}'
        }
        run_command = [CommandPerfEstimator._interpret_tags(s, tags_value) for s in self.run_command]
        run_command_cwd = CommandPerfEstimator._interpret_tags(str(self.run_command_cwd), tags_value)
        stdout_filepath = None
        if self.stdout_filepath is not None:
            stdout_filepath = CommandPerfEstimator._interpret_tags(str(self.stdout_filepath), tags_value)
        stderr_filepath = None
        if self.stderr_filepath is not None:
            stderr_filepath = CommandPerfEstimator._interpret_tags(str(self.stderr_filepath), tags_value)
        with self._runs_lock:
            run = Run(self._next_run_id, worker_id)
            self._next_run_id += 1
            _run_thread = self.popen_and_call(popen_args=run_command, on_exit=self.on_exit, run_id=run.id, cwd=run_command_cwd, stdout_filepath=stdout_filepath, stderr_filepath=stderr_filepath)  # noqa:F841
            self._runs[run.id] = run

    def run(self) -> DurationInSeconds:
        '''performs the runs of the command and returns the runs' average duration'''
        print(f"executing the following command in parallel ({self.num_parallel_runs} parallel runs) : '{str(self.run_command)}'")
        for worker_id in range(self.num_parallel_runs):
            self._start_run(worker_id)
        # wait until all runs have finished
        self._finished_event.wait()
        with self._runs_lock:
            workers_success = [run.return_code == 0 for run in self._runs.values()]
            if not all(workers_success):
                raise StarBenchException(f'at least one run failed (workers_success = {workers_success})')
        mean_duration, num_runs = self.get_run_mean_duration()
        print(f'mean duration : {mean_duration:.3f} s ({num_runs} runs)')
        return mean_duration


# def test_starbencher():
#     if False:
#         stop_condition = StopAfterSingleRun()
#         # stop_condition = StopWhenConverged(max_error=0.0001)
#         bench = StarBencher(run_command=['sleep', '0.1415927'], num_cores_per_run=1, num_parallel_runs=2, max_num_cores=2, stop_condition=stop_condition)
#         mean_duration = bench.run()
#         print(mean_duration)

#     if False:
#         bench = StarBencher(run_command=['ls', '/tmp'], num_cores_per_run=1, num_parallel_runs=2, max_num_cores=2, max_error=0.0001)
#         mean_duration = bench.run()
#         print(mean_duration)
#     pass

# end of starbencher


def starbench_cmake_app(git_repos_url: str, code_version: str, tmp_dir: Path, num_cores: int, git_user: str, git_password: str, benchmark_command: List[str], cmake_options: List[str] = None, cmake_exe_location: Path = None):
    """
    tests_to_run : regular expression as understood by ctest's -L option. eg '^arch4_quick$'
    """
    tmp_dir.mkdir(exist_ok=True)
    git_credentials = []
    if git_user:
        git_credentials.append(git_user)
    if git_password:
        git_credentials.append(git_password)
    if len(git_credentials) != 0:
        git_repos_url = git_repos_url.replace('https://', f"https://{':'.join(git_credentials)}@")
    src_dir = tmp_dir / 'source.git'
    # src_dir.mkdir(exist_ok=True)
    subprocess.run(['git', 'clone', f'{str(git_repos_url)}', str(src_dir)], cwd=str(tmp_dir), check=True)
    if code_version:
        subprocess.run(['git', 'checkout', f'{code_version}'], cwd=str(src_dir), check=True)

    # we need one build for each parallel run, otherwise running ctest on parallel would overwrite the same file, which causes the test to randomly fail depnding on race conditions
    worker_dir = tmp_dir / 'worker<worker_id>'
    build_dir = worker_dir / 'build'
    print(f'creating build directory {worker_dir}')
    create_build_dir = CommandPerfEstimator(
        run_command=['mkdir', '-p', build_dir],
        num_cores_per_run=1,
        num_parallel_runs=num_cores,
        max_num_cores=num_cores,
        stop_condition=StopAfterSingleRun(),
        run_command_cwd=Path('/tmp'),
        stdout_filepath=None)
    _create_build_dir_duration = create_build_dir.run()  # noqa: F841
    # build_dir.mkdir(exist_ok=True)

    print(f'configuring {src_dir} into {build_dir} ...')
    cmake_prog = 'cmake'
    if cmake_exe_location:
        cmake_prog = str(cmake_exe_location)
    configure = CommandPerfEstimator(
        run_command=[cmake_prog] + cmake_options + [src_dir],
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

    starbench_cmake_app(git_repos_url=git_repos_url, code_version=args.code_version, tmp_dir=args.output_dir, num_cores=args.num_cores, git_user=git_user, git_password=git_password, cmake_options=args.cmake_option, benchmark_command=args.benchmark_command.split(' '), cmake_exe_location=args.cmake_path)


if __name__ == '__main__':
    main()

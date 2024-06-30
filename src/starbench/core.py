#!/usr/bin/env python3
'''starbench is an application that is able to measure the execution time of a user software suite in various conditions (different build modes and different execution modes)

'''
__version__ = '1.0.0'
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
Url = str
GitCommitId = str


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
            assert isinstance(untagged_string, str)
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
            Path(stdout_filepath).parent.mkdir(exist_ok=True)
        stderr_filepath = None
        if self.stderr_filepath is not None:
            stderr_filepath = CommandPerfEstimator._interpret_tags(str(self.stderr_filepath), tags_value)
            Path(stderr_filepath).parent.mkdir(exist_ok=True)

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

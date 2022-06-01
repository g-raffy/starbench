#!/usr/bin/env python3
# this script performs a performance benchmark of hibridon using ipr (Institut de Physique de Rennes)'s cluster
import threading
import subprocess
import os
from typing import List, Dict  # , Set, , Tuple, Optional
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import ForwardRef


class Run():

    def __init__(self, run_id: int, worker_id: int):
        self.id = run_id
        self.worker_id = worker_id  # the worker used for this run (number of workers = number of parallel runs)
        self.pid = None
        self.return_code = 0
        self.start_time = datetime.now()
        self.end_time = None

    def has_finished(self):
        return self.end_time is not None

    def get_duration(self):
        assert self.has_finished()
        return (self.end_time - self.start_time).total_seconds()


StarBencher = ForwardRef('StarBencher')


class IStarBencherStopCondition(ABC):

    @abstractmethod
    def should_stop(self, star_bencher: StarBencher):
        pass


class StopAfterSingleRun(IStarBencherStopCondition):

    def __init__(self):
        pass

    def should_stop(self, star_bencher: StarBencher):
        # never start a new run
        return True


class StopWhenConverged(IStarBencherStopCondition):

    def __init__(self, max_error: float = 0.01):
        self.max_error = max_error
        self._last_mean_duration = None

    def should_stop(self, star_bencher: StarBencher):
        do_stop = False
        mean_duration, num_runs = star_bencher._get_run_mean_duration()
        print('mean_duration = %f' % mean_duration)
        if self._last_mean_duration is not None:
            diff = abs(mean_duration - self._last_mean_duration)
            print('diff = %f' % diff)
            if diff < self.max_error:
                do_stop = True
        self._last_mean_duration = mean_duration
        return do_stop


class StarBencher():
    '''
    the 'star' term comes from hpl's stadgemm benchmark, where we launch `n` independent programs on `n cores`
    '''

    def __init__(self, run_command: List[str], num_cores_per_run: int, num_parallel_runs: int, max_num_cores: int, stop_condition: IStarBencherStopCondition, stop_on_error=True, run_command_cwd: Path = None, stdout_filepath: Path = None, stderr_filepath: Path = None):
        assert num_cores_per_run * num_parallel_runs <= max_num_cores
        self.run_command: List[str] = run_command
        self.run_command_cwd = run_command_cwd
        self.stdout_filepath = stdout_filepath
        self.stderr_filepath = stderr_filepath
        self.num_cores_per_run = num_cores_per_run
        self.num_parallel_runs = num_parallel_runs
        self.max_num_cores: int = max_num_cores
        self.stop_condition: IStarBencherStopCondition = stop_condition
        self.stop_on_error = stop_on_error
        self._next_run_id: int = 0
        self._runs: Dict(int, Run) = {}
        self._last_mean_duration = None
        self._num_runs = 0
        self._runs_lock = threading.Lock()
        self._finished_event = threading.Event()

    def popen_and_call(self, popen_args, on_exit, run_id: int, cwd: Path, stdout_filepath: Path = None, stderr_filepath: Path = None):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        on_exit when the subprocess completes.
        on_exit is a callable object, and popen_args is a list/tuple of args that
        would give to subprocess.Popen.
        """
        def run_in_thread(popen_args, on_exit):
            stdout = None
            stderr = None
            if stdout_filepath is not None:
                stdout = open(stdout_filepath, 'w')
            if stderr_filepath is not None:
                stderr = open(stderr_filepath, 'w')
            proc = subprocess.Popen(popen_args, cwd=cwd, stdout=stdout, stderr=stderr)
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

    def _get_run_mean_duration(self):
        duration_sums: float = 0.0
        num_finished_runs: int = 0
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

    def on_exit(self, pid: int, return_code: int, run_id: int):
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

    def _start_run(self, worker_id: int):
        worker_as_str = '%03d' % worker_id
        run_command = [str(s).replace('<worker_id>', worker_as_str) for s in self.run_command]
        run_command_cwd = str(self.run_command_cwd).replace('<worker_id>', worker_as_str)
        stdout_filepath = None
        if self.stdout_filepath is not None:
            stdout_filepath = str(self.stdout_filepath).replace('<worker_id>', worker_as_str)
        stderr_filepath = None
        if self.stderr_filepath is not None:
            stderr_filepath = str(self.stderr_filepath).replace('<worker_id>', worker_as_str)
        run_command_cwd = str(self.run_command_cwd).replace('<worker_id>', worker_as_str)
        with self._runs_lock:
            run = Run(self._next_run_id, worker_id)
            self._next_run_id += 1
            run_thread = self.popen_and_call(popen_args=run_command, on_exit=self.on_exit, run_id=run.id, cwd=run_command_cwd, stdout_filepath=stdout_filepath, stderr_filepath=stderr_filepath)  # noqa:F841
            self._runs[run.id] = run

    def run(self):
        for worker_id in range(self.num_parallel_runs):
            self._start_run(worker_id)
        # wait until all runs have finished
        self._finished_event.wait()
        with self._runs_lock:
            if not all([run.return_code == 0 for run in self._runs.values()]):
                raise Exception('at least one run failed')
        mean_duration, num_runs = self._get_run_mean_duration()
        print('mean duration : %.3f s (%d runs)' % (mean_duration, num_runs))
        return mean_duration


def measure_hibridon_perf(hibridon_version: str, tmp_dir: Path, num_cores: int, github_username: str, github_personal_access_token: str):
    tmp_dir.mkdir(exist_ok=True)
    hibridon_git_url = 'https://%s:%s@github.com/hibridon/hibridon' % (github_username, github_personal_access_token)
    subprocess.run(['git', 'clone', '%s' % (hibridon_git_url)], cwd=tmp_dir)
    src_dir = tmp_dir / 'hibridon'
    src_dir.mkdir(exist_ok=True)
    subprocess.run(['git', 'checkout', '%s' % (hibridon_version)], cwd=src_dir)
    assert src_dir.exists()

    for compiler in ['gfortran']:  # , 'ifort']:
        # we need one build for each parallel run, otherwise running ctest on parallel would overwrite the same file, which causes the test to randomkly fail depnding on race conditions
        build_dir = tmp_dir / compiler / 'worker<worker_id>'
        print('creating build directory %s' % build_dir)
        create_build_dir = StarBencher(
            run_command=['mkdir', '-p', build_dir],
            num_cores_per_run=1,
            num_parallel_runs=num_cores,
            max_num_cores=num_cores,
            stop_condition=StopAfterSingleRun(),
            run_command_cwd=Path('/tmp'),
            stdout_filepath=None)
        create_build_dir_duration = create_build_dir.run()  # noqa: F841
        # build_dir.mkdir(exist_ok=True)

        print('configuring %s into %s ...' % (src_dir, build_dir))
        configure = StarBencher(
            run_command=['cmake', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=ON', src_dir],
            num_cores_per_run=1,
            num_parallel_runs=num_cores,
            max_num_cores=num_cores,
            stop_condition=StopAfterSingleRun(),
            run_command_cwd=build_dir,
            stdout_filepath=build_dir / 'configure_stdout.txt',
            stderr_filepath=build_dir / 'configure_stderr.txt')
        configure_duration = configure.run()  # noqa: F841

        print('building %s ...' % (build_dir))
        build = StarBencher(
            run_command=['make'],
            num_cores_per_run=1,
            num_parallel_runs=num_cores,
            max_num_cores=num_cores,
            stop_condition=StopAfterSingleRun(),
            run_command_cwd=build_dir,
            stdout_filepath=build_dir / 'build_stdout.txt',
            stderr_filepath=build_dir / 'build_stderr.txt')
        build_duration = build.run()  # noqa: F841

        print('benchmarking %s ...' % (build_dir))
        stop_condition = StopAfterSingleRun()
        bench = StarBencher(
            run_command=['ctest', '--output-on-failure', '-L', '^arch4_quick$'],
            num_cores_per_run=1,
            num_parallel_runs=num_cores,
            max_num_cores=num_cores,
            stop_condition=stop_condition,
            run_command_cwd=build_dir,
            stdout_filepath=build_dir / 'bench_stdout.txt',
            stderr_filepath=build_dir / 'bench_stderr.txt')
        mean_duration = bench.run()
        print('duration for compiler %s : %.3f s' % (compiler, mean_duration))


if __name__ == '__main__':
    if True:
        github_username = 'g-raffy'  # os.environ['HIBRIDON_REPOS_USER']
        with open('%s/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat' % os.environ['HOME'], 'r') as f:
            github_personal_access_token = f.readline().replace('\n', '')  # os.environ['HIBRIDON_REPOS_PAT']
        # print('coucou', github_personal_access_token[-1])
        hibridon_version = '02aeb2c2da5ebe0f7301c9909aa623864e562c71'
        tmp_dir = Path('/tmp/hibridon_perf')
        measure_hibridon_perf(hibridon_version, tmp_dir, num_cores=2, github_username=github_username, github_personal_access_token=github_personal_access_token)

    if False:
        stop_condition = StopAfterSingleRun()
        # stop_condition = StopWhenConverged(max_error=0.0001)
        bench = StarBencher(run_command=['sleep', '0.1415927'], num_cores_per_run=1, num_parallel_runs=2, max_num_cores=2, stop_condition=stop_condition)
        mean_duration = bench.run()

    if False:
        bench = StarBencher(run_command=['ls', '/tmp'], num_cores_per_run=1, num_parallel_runs=2, max_num_cores=2, max_error=0.0001)
        mean_duration = bench.run()

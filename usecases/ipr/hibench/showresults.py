#!/usr/bin/env python3
from typing import Dict, List
from pathlib import Path
import re
import pandas as pd


CpuId = str  # eg 'intel_xeon_gold_6248r'
Speed = float  # the execution speed for a given job (1.0/job duration), in s^-1
Duration = float  # the duration of a run for a given job (in seconds)


class StarbenchMeasure():
    worker_durations: List[Duration]

    def __init__(self):
        self.worker_durations = []

    def get_average_duration(self) -> Speed:
        return sum(self.worker_durations) / len(self.worker_durations)

    def get_average_speed(self) -> Speed:
        return 1.0 / self.get_average_duration()


class HibenchResultsParser():

    @staticmethod
    def parse_bench_stdout(bench_stdout_file_path: Path) -> Duration:
        """
        bench_stdout_file_path: eg '/home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results/53894da48505892bfa05693a52312bacb12c70c9/nh3h2_qma_long/intel_xeon_x5550/ifort/worker000/bench_stdout.txt'
        """
        duration = None
        with open(bench_stdout_file_path, 'rt', encoding='utf8') as f:
            for line in f.readlines():
                match = re.match(r'Total Test time \(real\) = (?P<duration>[0-9.]+) sec', line)
                if match:
                    duration = float(match['duration'])
                    break
        return duration

    @staticmethod
    def parse_results(starbench_results_root: Path) -> pd.DataFrame:
        """reads the output files of a starbench_results_root
        """
        results = pd.DataFrame(columns=['commit-id', 'test-id', 'cpu-id', 'compiler-id', 'avg-duration'])
        for commit_path in starbench_results_root.iterdir():
            if not commit_path.is_dir():
                continue
            commit_id = commit_path.name  # eg dd0f413b85cf0f727a5a4e88b2b02d75a28b377f
            for test_path in commit_path.iterdir():
                if not test_path.is_dir():
                    continue
                test_id = test_path.name  # eg nh3h2_qma_long
                for cpu_path in test_path.iterdir():
                    if not cpu_path.is_dir():
                        continue
                    cpu_id = cpu_path.name  # eg intel_xeon_gold_6248r
                    for compiler_path in cpu_path.iterdir():
                        if not compiler_path.is_dir():
                            continue
                        compiler_id = compiler_path.name  # eg ifort
                        measure = StarbenchMeasure()
                        for worker_path in compiler_path.iterdir():
                            if not worker_path.is_dir():
                                continue
                            worker_id = worker_path.name
                            match = re.match(r'worker(?P<worker_index>[0-9][0-9][0-9])', worker_id)
                            if match is None:
                                print(f'unexpected path : {worker_path}')
                                continue
                            # worker_index = int(match['worker_index'])

                            duration = HibenchResultsParser.parse_bench_stdout(worker_path / 'bench_stdout.txt')
                            measure.worker_durations.append(duration)
                        if len(measure.worker_durations) > 0:
                            results.loc[results.shape[0]] = [commit_id, test_id, cpu_id, compiler_id, measure.get_average_duration()]
        return results


def main():

    # 20240927-20:03:18 graffy@graffy-ws2:~/work/starbench/starbench.git$ rsync -va graffy@physix.ipr.univ-rennes1.fr:/opt/ipr/cluster/work.global/graffy/hibridon/benchmarks/starbench/ ./usecases/ipr/hibench/results/
    hiperf = HibenchResultsParser.parse_results(Path('/home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results'))
    print(hiperf)


main()

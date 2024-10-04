#!/usr/bin/env python3
from typing import Dict, List, Any
from pathlib import Path
import re
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, text

CpuId = str  # eg 'intel_xeon_gold_6248r'
Speed = float  # the execution speed for a given job (1.0/job duration), in s^-1
Duration = float  # the duration of a run for a given job (in seconds)
HostFqdn = str  # host fully qualified domain name, eg physix12.ipr.univ-rennes1.fr


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
    def parse_maths_lib_paths(math_lib_paths: str) -> Dict[str, str]:
        lib_info = {}
        for path in math_lib_paths.split(';'):
            if path.find('compilers_and_libraries_2020.1.217') != -1:
                # graffy@physix-frontal:~$ module show lib/mkl/2020.0.1
                # -------------------------------------------------------------------
                # /usr/share/modules/modulefiles/lib/mkl/2020.0.1:

                # module-whatis	 Sets the Environment to use the Intel Math Kernel Libraries version 2020.0.1
                # setenv		 MKLROOT /opt/intel/compilers_and_libraries_2020.1.217/linux/mkl
                lib_info['lib_name'] = 'mkl'
                lib_info['lib_version'] = '2020.0.1'
                break
            elif path.find('/usr/lib/libblas.so') != -1:
                # graffy@physix-frontal:~$ ls -l /usr/lib/libblas.so
                # lrwxrwxrwx 1 root root 28 Jun  4  2018 /usr/lib/libblas.so -> /etc/alternatives/libblas.so
                # graffy@physix-frontal:~$ ls -l /etc/alternatives/libblas.so
                # lrwxrwxrwx 1 root root 36 Jul 29  2020 /etc/alternatives/libblas.so -> /usr/lib/atlas-base/atlas/libblas.so
                # graffy@physix-frontal:~$ ls -l /usr/lib/atlas-base/atlas/libblas.so
                # lrwxrwxrwx 1 root root 12 Aug  6  2016 /usr/lib/atlas-base/atlas/libblas.so -> libblas.so.3
                # graffy@physix-frontal:~$ dpkg -l | grep atlas
                # ii  libatlas-base-dev                                                3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, generic static
                # ii  libatlas-dev                                                     3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, C header files
                # ii  libatlas3-base                                                   3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, generic shared
                lib_info['lib_name'] = 'atlas'
                lib_info['lib_version'] = 'debian_3.10.3-1+b1'
                break
            elif path.find('/usr/lib/liblapack.so') != -1:
                # /usr/lib/liblapack.so;/usr/lib/libblas.so;/usr/lib/libf77blas.so;/usr/lib/libatlas.so
                # graffy@physix-frontal:~$ ls -l /usr/lib/liblapack.so
                # lrwxrwxrwx 1 root root 30 Jun  4  2018 /usr/lib/liblapack.so -> /etc/alternatives/liblapack.so
                # graffy@physix-frontal:~$ ls -l /etc/alternatives/liblapack.so
                # lrwxrwxrwx 1 root root 38 Jul 29  2020 /etc/alternatives/liblapack.so -> /usr/lib/atlas-base/atlas/liblapack.so
                # graffy@physix-frontal:~$ ls -l /usr/lib/atlas-base/atlas/liblapack.so
                # lrwxrwxrwx 1 root root 14 Aug  6  2016 /usr/lib/atlas-base/atlas/liblapack.so -> liblapack.so.3
                # graffy@physix-frontal:~$ dpkg -l | grep atlas
                # ii  libatlas-base-dev                                                3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, generic static
                # ii  libatlas-dev                                                     3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, C header files
                # ii  libatlas3-base                                                   3.10.3-1+b1                       amd64        Automatically Tuned Linear Algebra Software, generic shared
                lib_info['lib_name'] = 'atlas'
                lib_info['lib_version'] = 'debian_3.10.3-1+b1'
                break
            else:
                assert False, f'unexpected value for blas_paths: {math_lib_paths}'
        return lib_info

    @staticmethod
    def parse_configure_stdout(configure_stdout_file_path: Path) -> Dict[str, Any]:
        # -- The C compiler identification is GNU 6.3.0
        # -- The CXX compiler identification is GNU 6.3.0
        # -- Detecting C compiler ABI info
        # -- Detecting C compiler ABI info - done
        # -- Check for working C compiler: /usr/bin/cc - skipped
        # -- Detecting C compile features
        # -- Detecting C compile features - done
        # -- Detecting CXX compiler ABI info
        # -- Detecting CXX compiler ABI info - done
        # -- Check for working CXX compiler: /usr/bin/c++ - skipped
        # -- Detecting CXX compile features
        # -- Detecting CXX compile features - done
        # -- The Fortran compiler identification is Intel 19.1.0.20200306
        # -- Detecting Fortran compiler ABI info
        # -- Detecting Fortran compiler ABI info - done
        # -- Check for working Fortran compiler: /opt/intel/compilers_and_libraries_2020.1.217/linux/bin/intel64/ifort - skipped
        # -- Looking for pthread.h
        # -- Looking for pthread.h - found
        # -- Performing Test CMAKE_HAVE_LIBC_PTHREAD
        # -- Performing Test CMAKE_HAVE_LIBC_PTHREAD - Failed
        # -- Looking for pthread_create in pthreads
        # -- Looking for pthread_create in pthreads - not found
        # -- Looking for pthread_create in pthread
        # -- Looking for pthread_create in pthread - found
        # -- Found Threads: TRUE  
        # -- Looking for Fortran sgemm
        # -- Looking for Fortran sgemm - found
        # -- Looking for Fortran cheev
        # -- Looking for Fortran cheev - found
        # -- Configuring done
        # -- Generating done
        # -- Build files have been written to: /mnt/workl/146180.1.long.q/graffy/146180/worker000/build
        build_config_info = {}
        with open(configure_stdout_file_path, 'rt', encoding='utf8') as f:
            for line in f.readlines():
                # -- The Fortran compiler identification is Intel 19.1.0.20200306
                # -- The Fortran compiler identification is GNU 6.3.0
                print(line)
                match = re.match(r'^-- The Fortran compiler identification is (?P<fortran_compiler_id>.+)$', line)
                if match:
                    fortran_compiler_id = match['fortran_compiler_id']
                    match = re.match(r'^(?P<fortran_compiler_provider_id>[a-zA-Z]+) (?P<compiler_version>.+)$', fortran_compiler_id)
                    assert match, f'unable to parse {fortran_compiler_id}'
                    build_config_info['fortran_compiler'] = {
                        'Intel': 'ifort',
                        'GNU': 'gfortran'
                    }[match['fortran_compiler_provider_id']]
                    build_config_info['fortran_compiler_version'] = match['compiler_version']
                # -- Found BLAS: /opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_intel_lp64.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_intel_thread.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_core.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/compiler/lib/intel64_lin/libiomp5.so;-lpthread;-lm;-ldl  
                match = re.match(r'^-- Found BLAS: (?P<blas_paths>.+)$', line)
                if match:
                    lib_info = HibenchResultsParser.parse_maths_lib_paths(match['blas_paths'])
                    build_config_info['blas'] = lib_info['lib_name']
                    build_config_info['blas_version'] = lib_info['lib_version']

                # -- Found LAPACK: /opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_intel_lp64.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_intel_thread.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/mkl/lib/intel64_lin/libmkl_core.so;/opt/intel/compilers_and_libraries_2020.1.217/linux/compiler/lib/intel64_lin/libiomp5.so;-lpthread;-lm;-ldl;-lpthread;-lm;-ldl
                match = re.match(r'^-- Found LAPACK: (?P<lapack_paths>.+)$', line)
                if match:
                    lib_info = HibenchResultsParser.parse_maths_lib_paths(match['lapack_paths'])
                    build_config_info['lapack'] = lib_info['lib_name']
                    build_config_info['lapack_version'] = lib_info['lib_version']
        assert 'fortran_compiler' in build_config_info.keys()
        assert 'blas' in build_config_info.keys()
        return build_config_info

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
    def parse_job_stdout(job_stdout_file_path: Path) -> Dict[str, Any]:
        """ parses files such as /home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results/53894da48505892bfa05693a52312bacb12c70c9/nh3h2_qma_long/intel_xeon_e5-2660/gfortran/hibench_intel_xeon_e5-2660_gfortran_53894da48505892bfa05693a52312bacb12c70c9.o146192
        """
        host_fqdn = None
        job_id = None
        submit_dir = None
        job_start_time = None
        with open(job_stdout_file_path, 'rt', encoding='utf8') as f:
            for line in f.readlines():
                # Executing job 145989 on physix48 from /mnt/work/graffy/hibridon/benchmarks/starbench/a3bed1c3ccfbca572003020d3e3d3b1ff3934fad/arch4_quick/intel_xeon_x5550/ifort/
                match = re.match(r'^Executing job (?P<job_id>[0-9]+) on (?P<hostname>[a-z0-9]+) from (?P<submit_dir>.+)$', line)
                if match:
                    job_id = match['job_id']
                    hostname = match['hostname']
                    submit_dir = Path(match['submit_dir'])
                    cluster_id = re.match(r'(?P<cluster_id>[a-z]+)(?P<cluster_index>[0-9]+)', hostname)['cluster_id']
                    domain = {
                        'physix': 'ipr.univ-rennes1.fr',
                        'alambix': 'ipr.univ-rennes.fr',
                    }[cluster_id]
                    host_fqdn = f'{hostname}.{domain}'
                # date: 2022-06-10T15:51:02+02:00
                match = re.match(r'^date: (?P<date>[0-9\-T:+]+)$', line)
                if match:
                    job_start_time = datetime.datetime.fromisoformat(match['date'])
                # the command /opt/ipr/cluster/work.local/146192.1.long.q/graffy/146192/starbench.py --git-repos-url https://github.com/hibridon/hibridon --git-user g-raffy --git-pass-file /mnt/home.ipr/graffy/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat --num-cores 16 --output-dir /opt/ipr/cluster/work.local/146192.1.long.q/graffy/146192 --code-version 53894da48505892bfa05693a52312bacb12c70c9 --cmake-path /opt/cmake/cmake-3.23.0/bin/cmake --cmake-option=-DCMAKE_BUILD_TYPE=Release --cmake-option=-DBUILD_TESTING=ON --cmake-option=-DCMAKE_Fortran_COMPILER=gfortran --benchmark-command="ctest --output-on-failure -L ^nh3h2_qma_long$" succeeded
        assert host_fqdn is not None
        return {
            'host_fqdn': host_fqdn,
            'job_id': job_id,
            'submit_dir': submit_dir,
            'job_start_time': job_start_time
        }

    @staticmethod
    def parse_results(starbench_results_root: Path) -> pd.DataFrame:
        """reads the output files of a starbench_results_root
        """
        results = pd.DataFrame(columns=['commit-id', 'test-id', 'cpu-id', 'fortran-compiler', 'fortran-compiler-version', 'blas', 'blas-version', 'lapack', 'lapack-version', 'avg-duration', 'host-fqdn', 'job_id', 'job_start_time', 'submit_dir'])
        # # set dtypes for each column
        # df['A'] = df['A'].astype(int)
        # df['B'] = df['B'].astype(float)
        # df['C'] = df['C'].astype(str)
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
                        host_fqdn = None
                        job_id = None
                        submit_dir = None
                        job_start_time = None
                        configure_stdout_path = compiler_path / 'worker000' / 'configure_stdout.txt'
                        if not configure_stdout_path.exists():
                            continue
                        build_config_info = HibenchResultsParser.parse_configure_stdout(configure_stdout_path)
                        print(build_config_info)

                        for child_path in compiler_path.iterdir():
                            if not child_path.is_dir():
                                if re.match(r'^hibench_[^.]+\.o[0-9]+$', child_path.name):
                                    job_stdout_file_path = child_path
                                    job_data = HibenchResultsParser.parse_job_stdout(job_stdout_file_path)
                                    host_fqdn = job_data['host_fqdn']
                                    job_id = job_data['job_id']
                                    submit_dir = job_data['submit_dir']
                                    job_start_time = job_data['job_start_time']
                            worker_id = child_path.name
                            match = re.match(r'worker(?P<worker_index>[0-9][0-9][0-9])', worker_id)
                            if match is None:
                                print(f'unexpected path : {child_path}')
                                continue
                            # worker_index = int(match['worker_index'])

                            duration = HibenchResultsParser.parse_bench_stdout(child_path / 'bench_stdout.txt')
                            measure.worker_durations.append(duration)
                        if len(measure.worker_durations) > 0:
                            results.loc[results.shape[0]] = [commit_id, test_id, cpu_id, build_config_info['fortran_compiler'], build_config_info['fortran_compiler_version'], build_config_info['blas'], build_config_info['blas_version'], build_config_info['lapack'], build_config_info['lapack_version'], measure.get_average_duration(), host_fqdn, job_id, job_start_time.isoformat(), str(submit_dir)]
        print(results.dtypes)
        return results


def get_cpu_freq(cpu_id: CpuId) -> float:
    return {
        'intel_xeon_x5550': 2.67,
        'intel_xeon_x5650': 2.67,
        'intel_xeon_e5-2660': 2.2,
        'intel_xeon_e5-2660v2': 2.2,
        'intel_xeon_e5-2660v4': 2.0,
        'intel_xeon_gold_5222': 3.8,
        'intel_xeon_gold_6140': 2.3,
        'intel_xeon_gold_6154': 3.0,
        'intel_xeon_gold_6226r': 2.9,
        'intel_xeon_gold_6248r': 3.0,
        'amd_epyc_7282': 2.8
    }[cpu_id] * 10**9


def create_graph(sql_engine, per_clock: bool):
    with sql_engine.connect() as conn:
        cpu_data = {}

        computation_id = 'nh3h2_qma_long'
        commit_ids = set()
        result = conn.execute(text('SELECT "cpu-id", "avg-duration", "commit-id" FROM hibench WHERE blas="mkl"'))
        for row in result:
            print(row)
            (cpu_id, avg_duration, commit_id) = row
            if cpu_id not in cpu_data.keys():
                cpu_data[cpu_id] = {}
            commit_id_to_avg_duration = cpu_data[cpu_id]
            commit_id_to_avg_duration[commit_id] = avg_duration
            commit_ids.add(commit_id)

        # print(mkl_perf)

        cpu_order = {
            'intel_xeon_x5550': 0,
            'intel_xeon_e5-2660': 1,
            'intel_xeon_e5-2660v2': 2,
            'intel_xeon_e5-2660v4': 3,
            'intel_xeon_gold_5222': 4,
            'intel_xeon_gold_6140': 5,
            'intel_xeon_gold_6154': 6,
            'intel_xeon_gold_6226r': 7,
            'intel_xeon_gold_6248r': 8,
            'amd_epyc_7282': 9
        }

        fig, ax = plt.subplots()
        cpu_ids = sorted(cpu_data.keys(), key=lambda x: cpu_order[x])
        x = np.arange(len(cpu_ids))  # the label locations
        bar_group_width = 0.8
        bar_width = bar_group_width / len(commit_ids)  # the width of the bars

        commit_index = 0
        for commit_id in commit_ids:
            # print(f'commit {commit_id}')
            y = []
            for cpu_id in cpu_ids:
                commit_id_to_avg_duration = cpu_data[cpu_id]
                # print(perfs)
                cpu_y = 0.0
                print(commit_id_to_avg_duration)
                if commit_id in commit_id_to_avg_duration:
                    cpu_y = 1.0 / commit_id_to_avg_duration[commit_id]
                if per_clock:
                    cpu_y /= get_cpu_freq(cpu_id)
                y.append(cpu_y)
            bar_x_pos = x - bar_group_width * 0.5 + bar_group_width * ((commit_index + 0.5) / len(commit_ids))
            print(commit_index, bar_x_pos)
            rects = ax.bar(bar_x_pos, y, bar_width, label=f'hibridon {commit_id}')
            commit_index += 1

        # Add some text for labels, title and custom x-axis tick labels, etc.
        if per_clock:
            ylabel = 'number of computations per cpu clock for a core'
        else:
            ylabel = 'number of computations per second for a core'
        ax.set_ylabel(ylabel)
        ax.set_title(f'hibridon\'s {computation_id} performance (serial code) on various cpus')
        ax.set_xticks(x)
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_xticklabels(cpu_ids)
        ax.legend()

        if False:
            plt.style.use('_mpl-gallery')

            # make data:
            x = 0.5 + np.arange(8)
            y = [4.8, 5.5, 3.5, 4.6, 6.5, 6.6, 2.6, 3.0]

            # plot
            fig, ax = plt.subplots()

            ax.bar(x, y, width=1, edgecolor="white", linewidth=0.7)

            ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
                   ylim=(0, 8), yticks=np.arange(1, 8))

        if False:
            labels = ['G1', 'G2', 'G3', 'G4', 'G5']
            men_means = [20, 34, 30, 35, 27]
            women_means = [25, 32, 34, 20, 25]

            x = np.arange(len(labels))  # the label locations
            width = 0.35  # the width of the bars

            fig, ax = plt.subplots()


            rects1 = ax.bar(x - width/2, men_means, width, label='Men')
            rects2 = ax.bar(x + width/2, women_means, width, label='Women')

            # Add some text for labels, title and custom x-axis tick labels, etc.
            ax.set_ylabel('Scores')
            ax.set_title('Scores by group and gender')
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()

        plt.show()


def create_graphs(sql_engine):
    create_graph(sql_engine, per_clock=True)


def main():

    # 20240927-20:03:18 graffy@graffy-ws2:~/work/starbench/starbench.git$ rsync -va graffy@physix.ipr.univ-rennes1.fr:/opt/ipr/cluster/work.global/graffy/hibridon/benchmarks/starbench/ ./usecases/ipr/hibench/results/
    hiperf = HibenchResultsParser.parse_results(Path('/home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results'))
    hiperf.to_csv('/home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results.csv')
    print(hiperf)
    engine = create_engine('sqlite://', echo=False)  # Turning echo to True just logs SQL statements, I'd avoid parsing this logs
    # hiperf.to_sql(name='Auto', con=engine)
    # hiperf.reset_index().to_sql(name='hibench', con=engine)  # reset_index() is needed to preserve index column in dumped data
    hiperf.to_sql(name='hibench', con=engine)  # reset_index() is needed to preserve index column in dumped data

    with engine.connect() as conn, open('/home/graffy/work/starbench/starbench.git/usecases/ipr/hibench/results.sql', 'wt', encoding='utf8') as sql_file:
        for line in conn.connection.iterdump():
            sql_file.write(line)
            sql_file.write('\n')

    create_graphs(engine)


main()

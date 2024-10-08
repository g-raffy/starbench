#!/usr/bin/env python3
# this script launches jobs to run hibridon benchmarks on physix cluster for the given version of hibridon (commit number)
from typing import List, Tuple, Dict
from argparse import ArgumentParser
import os
from os import getenv, makedirs
import shutil
from pathlib import Path
import subprocess
import re

HostFqdn = str  # eg 'physix90.ipr.univ-rennes1.fr'
GitCommitTag = str  # commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
HostGroupId = str  # eg 'xeon_gold_6140'
CompilerId = str  # eg 'gfortran'


def substitute_tag_with_filecontents(input_file_path: Path, tag: str, contents_file: Path, output_file_path: Path):
    contents = open(contents_file, 'rt', encoding='utf8').read()
    with open(input_file_path, 'rt', encoding='utf8') as template_file, open(output_file_path, 'wt', encoding='utf8') as out_file:
        for template_line in template_file.readlines():
            line = template_line.replace(tag, contents)
            out_file.write(line)


def substitute_tags(input_file_path: Path, tags_dict: Dict[str, str], output_file_path: Path):
    with open(input_file_path, 'rt', encoding='utf8') as template_file, open(output_file_path, 'wt', encoding='utf8') as out_file:
        for template_line in template_file.readlines():
            line = template_line
            for tag, value in tags_dict.items():
                if re.match(r'<include:', tag) is not None:
                    contents = open(value, 'rt', encoding='utf8').read()
                else:
                    contents = value
                line = line.replace(tag, contents)
            out_file.write(line)


class ClusterNodeDef:
    host_fqdn: str
    cpu_id: str
    num_cpus: int

    def __init__(self, host_fqdn: str, cpu_id: str, num_cpus: int):
        self.host_fqdn = host_fqdn
        self.cpu_id = cpu_id
        self.num_cpus = num_cpus


class CpuDef:
    cpu_id: str
    num_cores: int

    def __init__(self, cpu_id: str, num_cores: int):
        self.cpu_id = cpu_id
        self.num_cores = num_cores


class ClusterNodeDb:
    cluster_nodes_defs: List[ClusterNodeDef]
    cpu_defs: Dict[str, int]

    def __init__(self):
        self.cluster_nodes_defs = []
        self.add_cluster_node_def(ClusterNodeDef('alambix50.ipr.univ-rennes.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('alambix75.ipr.univ-rennes.fr', 'intel_xeon_e5-2660v2', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix103.ipr.univ-rennes.fr', 'amd_epyc_7452', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix104.ipr.univ-rennes.fr', 'intel_xeon_gold_6248r', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix105.ipr.univ-rennes.fr', 'intel_xeon_gold_6348', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix106.ipr.univ-rennes.fr', 'intel_xeon_gold_6348', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix107.ipr.univ-rennes.fr', 'intel_xeon_gold_6348', 2))
        self.add_cluster_node_def(ClusterNodeDef('alambix108.ipr.univ-rennes.fr', 'intel_xeon_gold_6348', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix12.ipr.univ-rennes1.fr', 'amd_epyc_7282', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix13.ipr.univ-rennes1.fr', 'amd_epyc_7282', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix14.ipr.univ-rennes1.fr', 'amd_epyc_7282', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix15.ipr.univ-rennes1.fr', 'amd_epyc_7282', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix48.ipr.univ-rennes1.fr', 'intel_xeon_x5550', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix49.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix51.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix52.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix53.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix54.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix55.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix56.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix57.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix58.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix59.ipr.univ-rennes1.fr', 'intel_xeon_x5650', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix60.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix61.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix62.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix63.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix64.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix65.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix66.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix67.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix68.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix69.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix70.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix71.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix72.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix73.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix74.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix76.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix77.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix78.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix79.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix80.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix81.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix82.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix83.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v2', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix84.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v4', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix85.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v4', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix86.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v4', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix87.ipr.univ-rennes1.fr', 'intel_xeon_e5-2660v4', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix88.ipr.univ-rennes1.fr', 'intel_xeon_gold_6140', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix89.ipr.univ-rennes1.fr', 'intel_xeon_gold_6140', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix90.ipr.univ-rennes1.fr', 'intel_xeon_gold_6154', 4))
        # self.add_cluster_node_def(ClusterNodeDef('physix91.ipr.univ-rennes1.fr', 'intel_xeon_gold_6140', 4))
        # self.add_cluster_node_def(ClusterNodeDef('physix92.ipr.univ-rennes1.fr', 'intel_xeon_gold_5220', 1))
        # self.add_cluster_node_def(ClusterNodeDef('physix93.ipr.univ-rennes1.fr', 'intel_xeon_gold_6226r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix94.ipr.univ-rennes1.fr', 'intel_xeon_gold_6226r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix95.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix96.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix97.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix98.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix99.ipr.univ-rennes1.fr', 'intel_xeon_gold_6240r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix100.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix101.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))
        # self.add_cluster_node_def(ClusterNodeDef('physix102.ipr.univ-rennes1.fr', 'intel_xeon_gold_6248r', 2))

        self.cpu_defs = {}
        self.add_cpu_def(CpuDef('intel_xeon_x5550', 4))
        self.add_cpu_def(CpuDef('intel_xeon_x5650', 6))
        self.add_cpu_def(CpuDef('intel_xeon_e5-2660', 8))
        self.add_cpu_def(CpuDef('intel_xeon_e5-2660v2', 10))
        self.add_cpu_def(CpuDef('intel_xeon_e5-2660v4', 14))
        self.add_cpu_def(CpuDef('intel_xeon_gold_6140', 18))
        self.add_cpu_def(CpuDef('intel_xeon_gold_6154', 18))
        self.add_cpu_def(CpuDef('intel_xeon_gold_5220', 4))
        self.add_cpu_def(CpuDef('intel_xeon_gold_6226r', 16))
        self.add_cpu_def(CpuDef('intel_xeon_gold_6248r', 24))
        self.add_cpu_def(CpuDef('intel_xeon_gold_6348', 28))
        self.add_cpu_def(CpuDef('amd_epyc_7282', 16))
        self.add_cpu_def(CpuDef('amd_epyc_7452', 32))

    def add_cluster_node_def(self, cluster_node_def: ClusterNodeDef):
        self.cluster_nodes_defs.append(cluster_node_def)

    def add_cpu_def(self, cpu_def: CpuDef):
        self.cpu_defs[cpu_def.cpu_id] = cpu_def

    def get_host_group_info(self, host_group_id: HostGroupId) -> Tuple[List[HostFqdn], int]:
        hosts = [cluster_node_def.host_fqdn for cluster_node_def in self.cluster_nodes_defs if cluster_node_def.cpu_id == host_group_id]
        num_cpus_set = set([cluster_node_def.num_cpus for cluster_node_def in self.cluster_nodes_defs if cluster_node_def.cpu_id == host_group_id])
        assert len(num_cpus_set) > 0
        assert len(num_cpus_set) <= 1, f'the number of cpus for the host group {host_group_id} is not homogen ({num_cpus_set})'
        num_cpus = num_cpus_set.pop()
        num_cores = self.cpu_defs[host_group_id].num_cores * num_cpus
        return (hosts, num_cores)


def launch_job_for_host_group(hibridon_version: GitCommitTag, host_group_id: HostGroupId, results_dir: Path, compiler_id: CompilerId):

    cluster_db = ClusterNodeDb()

    (hosts, num_cores) = cluster_db.get_host_group_info(host_group_id)

    # quick_test = 'arch4_quick'  # about 2s on a core i5 8th generation
    representative_test = 'nh3h2_qma_long'  # about 10min on a core i5 8th generation
    benchmark_test = representative_test
    if benchmark_test == 'arch4_quick':
        ram_per_core = '1G'
    elif benchmark_test == 'nh3h2_qma_long':
        ram_per_core = '2.8G'  # this was enough on physix48, but maybe we can reduce more
    else:
        assert f'unhandled benchmark_test : {benchmark_test}'

    git_repos_url = 'https://github.com/hibridon/hibridon'
    git_user = 'g-raffy'  # os.environ['HIBRIDON_REPOS_USER']
    git_pass_file = f'{getenv("HOME")}/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat'
    cmake_options = [
        '-DCMAKE_BUILD_TYPE=Release',  # build in release mode for highest performance
        '-DBUILD_TESTING=ON'  # enable hibridon tests
    ]

    benchmark_command = f'ctest --output-on-failure -L ^{benchmark_test}$'

    env_vars_bash_commands = ''
    if compiler_id == 'ifort':
        env_vars_bash_commands = 'module load compilers/ifort/latest'
        cmake_options.append('-DCMAKE_Fortran_COMPILER=ifort')  # use intel fortran compiler
        cmake_options.append('-DBLA_VENDOR=Intel10_64lp')  # use 64 bits intel mkl with multithreading
    elif compiler_id == 'gfortran':
        env_vars_bash_commands = ''
        cmake_options.append('-DCMAKE_Fortran_COMPILER=gfortran')  # use gfortran compiler
    else:
        assert f'unhandled compiler_id : {compiler_id}'

    makedirs(results_dir, exist_ok=True)

    this_bench_dir = Path(f'{results_dir}/{hibridon_version}/{benchmark_test}/{host_group_id}/{compiler_id}')
    makedirs(this_bench_dir, exist_ok=True)

    starbench_job_path = this_bench_dir / 'starbench.job'
    this_file_path = Path(os.path.realpath(__file__))
    scripts_dir = this_file_path.parent
    starbench_root_path = scripts_dir.parent.parent.parent  # TODO: beurk

    # create a copy of stargemm for use by the jobs (so that starbench_root_path can be modified without affecting the jobs)
    jobs_starbench_dir = results_dir / 'starbench'  # the location of starbench source code for use by the jobs run by this command
    shutil.copytree(starbench_root_path, jobs_starbench_dir, dirs_exist_ok=True)

    # create the job file (which embeds starbench.py)
    tags_dict = {
        # '<include:starbench.py>': scripts_dir / 'starbench.py',
        '<starbench_job_path>': str(starbench_job_path)
    }
    substitute_tags(input_file_path=scripts_dir / 'starbench-template.job', tags_dict=tags_dict, output_file_path=starbench_job_path)
    subprocess.run(['chmod', 'a+x', starbench_job_path], check=True)

    command = f'{starbench_job_path} "{git_repos_url}" "{git_user}" "{git_pass_file}" "{hibridon_version}" "{" ".join(cmake_options)}" "{benchmark_command}" "{env_vars_bash_commands}" "{starbench_root_path}"'
    print(f'command = {command}')

    qsub_command = 'qsub'
    qsub_command += f' -pe smp {num_cores}'
    qsub_command += f' -l "hostname={"|".join(hosts)}"'
    qsub_command += ' -S /bin/bash'
    qsub_command += ' -cwd'
    qsub_command += ' -m ae'
    qsub_command += f' -l mem_available={ram_per_core}'
    qsub_command += ' -j y'  # merge stderr file into stdout file for easier reading of history of events
    qsub_command += f' -N hibench_{host_group_id}_{compiler_id}_{hibridon_version}'
    qsub_command += f' {command}'
    print(f'qsub_command = {qsub_command}')

    subprocess.run(qsub_command, cwd=this_bench_dir, check=True, shell=True)


def launch_perf_jobs(hibridon_version: GitCommitTag, results_dir: Path):
    """
    hibridon_version: the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
    results_dir: where the results of the benchmark are stored (eg $GLOBAL_WORK_DIR/graffy/benchmarks/hibench)
    """

    compilers = [
        'gfortran',
        'ifort'
    ]

    host_groups = [
        'intel_xeon_x5550',
        'intel_xeon_x5650',
        'intel_xeon_e5-2660',
        'intel_xeon_e5-2660v2',
        'intel_xeon_e5-2660v4',
        'intel_xeon_gold_6140',
        'intel_xeon_gold_6154',
        'intel_xeon_gold_5222',
        'intel_xeon_gold_6226r',
        'intel_xeon_gold_6240r',
        'intel_xeon_gold_6248r',
        'amd_epyc_7282',
    ]

    for compiler in compilers:
        for host_group in host_groups:
            launch_job_for_host_group(hibridon_version, host_group, results_dir, compiler)


def path_is_reachable_by_compute_nodes(path: Path):
    path_is_reachable = False
    for shared_disk_path in [Path('/opt/ipr/cluster/work.global')]:
        try:
            _ = path.relative_to(shared_disk_path)
        except ValueError:
            continue
        path_is_reachable = True
        break
    return path_is_reachable


def main():
    arg_parser = ArgumentParser(description='launches hibridon benchmark jobs on IPR\'s physix cluster', epilog='example:\n    --commit-id a3bed1c3ccfbca572003020d3e3d3b1ff3934fad')
    arg_parser.add_argument('--commit-id', type=str, required=True, help='the commit id of the version of code to benchmark')
    arg_parser.add_argument('--results-dir', type=Path, required=True, help='the root directory of the tree where the results of the benchmarks are stored (eg $GLOBAL_WORK_DIR/graffy/benchmarks/hibench)')

    args = arg_parser.parse_args()
    hibridon_version = args.commit_id

    # the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
    # '53894da48505892bfa05693a52312bacb12c70c9'  # latest from branch master as of 10/06/2022 00:30
    # code_version='dd0f413b85cf0f727a5a4e88b2b02d75a28b377f'  # latest from branch graffy-issue51 as of 10/06/2022 00:30

    results_dir = Path(args.results_dir)
    if not path_is_reachable_by_compute_nodes(results_dir):
        raise ValueError('the results path is expected to be on a disk that is accessible to all cluster nodes, and it doesn\'t seem to be the case for {results_dir}')

    launch_perf_jobs(hibridon_version, results_dir)


main()

#!/usr/bin/env python3
# this script launches jobs to run hibridon benchmarks on physix cluster for the given version of hibridon (commit number)
from typing import List, Tuple
from argparse import ArgumentParser
import os
from os import getenv, makedirs
from pathlib import Path
import subprocess

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


def get_host_group_info(host_group_id: HostGroupId) -> Tuple[List[HostFqdn], int]:
    if host_group_id == 'intel_xeon_x5550':
        hosts = ['physix48.ipr.univ-rennes1.fr']
        num_cores = '8'
    elif host_group_id == 'intel_xeon_x5650':
        hosts = [
            'physix49.ipr.univ-rennes1.fr',
            'physix50.ipr.univ-rennes1.fr',
            'physix51.ipr.univ-rennes1.fr',
            'physix52.ipr.univ-rennes1.fr',
            'physix53.ipr.univ-rennes1.fr',
            'physix54.ipr.univ-rennes1.fr',
            'physix55.ipr.univ-rennes1.fr',
            'physix56.ipr.univ-rennes1.fr',
            'physix57.ipr.univ-rennes1.fr',
            'physix58.ipr.univ-rennes1.fr',
            'physix59.ipr.univ-rennes1.fr',]
        num_cores = '12'
    elif host_group_id == 'intel_xeon_e5-2660':
        hosts = [
            'physix60.ipr.univ-rennes1.fr',
            'physix61.ipr.univ-rennes1.fr',
            'physix62.ipr.univ-rennes1.fr',
            'physix63.ipr.univ-rennes1.fr',

            'physix64.ipr.univ-rennes1.fr',
            'physix65.ipr.univ-rennes1.fr',
            'physix66.ipr.univ-rennes1.fr',
            'physix67.ipr.univ-rennes1.fr',

            'physix68.ipr.univ-rennes1.fr',
            'physix69.ipr.univ-rennes1.fr',
            'physix70.ipr.univ-rennes1.fr',
            'physix71.ipr.univ-rennes1.fr']
        num_cores = '16'
    elif host_group_id == 'intel_xeon_e5-2660v2':
        hosts = [
            'physix72.ipr.univ-rennes1.fr',
            'physix73.ipr.univ-rennes1.fr',
            'physix74.ipr.univ-rennes1.fr',
            'physix75.ipr.univ-rennes1.fr',

            'physix76.ipr.univ-rennes1.fr',
            'physix77.ipr.univ-rennes1.fr',
            'physix78.ipr.univ-rennes1.fr',
            'physix79.ipr.univ-rennes1.fr',

            'physix80.ipr.univ-rennes1.fr',
            'physix81.ipr.univ-rennes1.fr',
            'physix82.ipr.univ-rennes1.fr',
            'physix84.ipr.univ-rennes1.fr']
        num_cores = '20'
    elif host_group_id == 'intel_xeon_e5-2660v4':
        hosts = [
            'physix84.ipr.univ-rennes1.fr',
            'physix85.ipr.univ-rennes1.fr',
            'physix86.ipr.univ-rennes1.fr',
            'physix87.ipr.univ-rennes1.fr']
        num_cores = '28'
    elif host_group_id == 'intel_xeon_gold_6140':
        hosts = [
            'physix88.ipr.univ-rennes1.fr',
            'physix89.ipr.univ-rennes1.fr']
        num_cores = '36'
    elif host_group_id == 'intel_xeon_gold_6154':
        hosts = [
            'physix90.ipr.univ-rennes1.fr']
        num_cores = '72'
    elif host_group_id == 'intel_xeon_gold_5222':
        hosts = [
            'physix92.ipr.univ-rennes1.fr']
        num_cores = '4'
    elif host_group_id == 'intel_xeon_gold_6226r':
        hosts = [
            'physix93.ipr.univ-rennes1.fr',
            'physix94.ipr.univ-rennes1.fr']
        num_cores = '32'
    elif host_group_id == 'intel_xeon_gold_6240r':
        hosts = [
            'physix99.ipr.univ-rennes1.fr']
        num_cores = '48'
    elif host_group_id == 'intel_xeon_gold_6248r':
        hosts = [
            'physix95.ipr.univ-rennes1.fr',
            'physix96.ipr.univ-rennes1.fr',
            'physix97.ipr.univ-rennes1.fr',
            'physix98.ipr.univ-rennes1.fr',
            'physix99.ipr.univ-rennes1.fr',
            'physix100.ipr.univ-rennes1.fr',
            'physix101.ipr.univ-rennes1.fr',
            'physix102.ipr.univ-rennes1.fr']
        num_cores = '48'
    elif host_group_id == 'amd_epyc_7282':
        hosts = [
            'physix12.ipr.univ-rennes1.fr',
            'physix13.ipr.univ-rennes1.fr',
            'physix14.ipr.univ-rennes1.fr',
            'physix15.ipr.univ-rennes1.fr']
        num_cores = '32'
    else:
        assert f"unhandled host_group_id : {host_group_id}"
    return (hosts, num_cores)


def launch_job_for_host_group(hibridon_version: GitCommitTag, host_group_id: HostGroupId, results_dir: Path, compiler_id: CompilerId):

    (hosts, num_cores) = get_host_group_info(host_group_id)

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
    this_file_path = os.path.realpath(__file__)
    scripts_dir = this_file_path.parent

    # create the job file (which embeds starbench.py)
    substitute_tag_with_filecontents(input_file_path=scripts_dir / 'starbench-template.job', tag='<include:starbench.py>', contents_file=scripts_dir / 'starbench.py', output_file_path=starbench_job_path)
    subprocess.run(f'chmod a+x {starbench_job_path}', check=True)

    command = f'{starbench_job_path} "{git_repos_url}" "{git_user}" "{git_pass_file}" "{hibridon_version}" "{" ".join(cmake_options)}" "{benchmark_command}" "{env_vars_bash_commands}"'
    print(f'command = {command}')

    qsub_command = 'qsub'
    qsub_command += f' -pe smp {num_cores}'
    qsub_command += f' -l "hostname={"|".join(hosts)}"'
    qsub_command += ' -cwd'
    qsub_command += ' -m ae'
    qsub_command += f' -l mem_available={ram_per_core}'
    qsub_command += ' -j y'  # merge stderr file into stdout file for easier reading of history of events
    qsub_command += f' -N hibench_{host_group_id}_{compiler_id}_{hibridon_version}'
    qsub_command += f' {command}'
    print(f'qsub_command = {qsub_command}')

    subprocess.run(qsub_command, cwd=this_bench_dir, check=True)


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

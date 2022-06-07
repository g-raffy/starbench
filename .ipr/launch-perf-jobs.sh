#!/usr/bin/env bash
# this script launches jobs to run hibridon benchmarks on physix cluster for the given version of hibridon (commit number)

function show_usage()
{
	echo "launches hibridon benchmark jobs on IPR's physix cluster"
	echo
	echo "syntax :"
	echo "    $0 <hibridon_version>"
	echo
	echo "example:"
	echo "    $0 a3bed1c3ccfbca572003020d3e3d3b1ff3934fad"
}

if [ "$#" != "1" ]
then
	show_usage
	exit 1
fi

HIBRIDON_VERSION="$1"  # the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
# 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'  # latest from branch master as of 01/06/2022 12:52
# code_version='775048db02dfb317d5eaddb6d6db520be71a2fdf'  # latest from branch graffy-issue51 as of 01/06/

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";


function substitute_TAG_with_FILEcontents {
  local TAG="${1}"
  local FILE="${2}"
  sed -e "/${TAG}/r ${FILE}" -e "/${TAG}/d"
}

function launch_job_for_host_group()
{
	local hibridon_version="$1" # the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
	local host_group_id="$2"  # eg 'xeon_gold_6140'
	local hosts=''
	local num_cores=''
	case "${host_group_id}" in
		'intel_xeon_gold_6140')
			hosts="${hosts}physix88.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix89.ipr.univ-rennes1.fr"
			num_cores='36'
			;;
		'intel_xeon_x5550')
			hosts="${hosts}physix48.ipr.univ-rennes1.fr"
			num_cores='8'
			;;
		*)
			error "unhandled host_group_id : ${host_group_id}"
			exit 1
			;;
	esac

	quick_test='arch4_quick'  # about 2s on a core i5 8th generation
	representative_test='nh3h2_qma_long'  # about 10min on a core i5 8th generation
	benchmark_test="${quick_test}"

	git_repos_url="https://github.com/hibridon/hibridon"
	git_user='g-raffy'  # os.environ['HIBRIDON_REPOS_USER']
	git_pass_file="$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat"
	cmake_options='-DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON'
	benchmark_command="ctest --output-on-failure -L ^${benchmark_test}\$"

	# cat $SCRIPT_DIR/hibench.job | sed "s~<include:starbench.py>~$(cat $SCRIPT_DIR/starbench.py)~" > /tmp/hibench.job
	cat $SCRIPT_DIR/hibench.job | substitute_TAG_with_FILEcontents '<include:starbench.py>' "$SCRIPT_DIR/starbench.py" > /tmp/hibench.job
	chmod a+x /tmp/hibench.job

	local hibench_root_dir="$GLOBAL_WORK_DIR/graffy/hibridon/benchmarks/starbench"
	mkdir -p "${hibench_root_dir}"

	local this_bench_dir="${hibench_root_dir}/${hibridon_version}/${benchmark_test}/${host_group_id}"
	mkdir -p "${this_bench_dir}"

	command="/tmp/hibench.job \"${git_repos_url}\" \"${git_user}\" \"${git_pass_file}\" \"${hibridon_version}\" \"${cmake_options}\" \"${benchmark_command}\""
	echo "command = $command"
		# eval $command

	pushd "${this_bench_dir}"

		qsub_command="qsub"
		qsub_command="${qsub_command} -pe smp ${num_cores}"
		qsub_command="${qsub_command} -l \"hostname=${hosts}\""
		qsub_command="${qsub_command} -cwd"
		qsub_command="${qsub_command} -m ae"
		qsub_command="${qsub_command} -l mem_available=1G"
		qsub_command="${qsub_command} -N ${benchmark_test}_${host_group_id}"
		qsub_command="${qsub_command} ${command}"
		# qsub -pe smp "$num_cores" -l "hostname=${hosts}" 
		echo "qsub_command = $qsub_command"
		eval $qsub_command
	popd
}


function launch_perf_jobs()
{
	local hibridon_version="$1" # the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'
	
	launch_job_for_host_group "${hibridon_version}" 'intel_xeon_x5550'
	#launch_job_for_host_group "${hibridon_version}" 'intel_xeon_gold_6140'
}


launch_perf_jobs "${HIBRIDON_VERSION}"
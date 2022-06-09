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
	local compiler_id="$3"  # eg 'gfortran' 'ifort'
	local hosts=''
	local num_cores=''
	case "${host_group_id}" in
		'intel_xeon_x5550')
			hosts="${hosts}physix48.ipr.univ-rennes1.fr"
			num_cores='8'
			;;
		'intel_xeon_x5650')
			hosts="${hosts}physix49.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix50.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix51.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix52.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix53.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix54.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix55.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix56.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix57.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix58.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix59.ipr.univ-rennes1.fr"
			num_cores='12'
			;;
		'intel_xeon_e5-2660')
			hosts="${hosts}physix60.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix61.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix62.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix63.ipr.univ-rennes1.fr"

			hosts="${hosts}|physix64.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix65.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix66.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix67.ipr.univ-rennes1.fr"

			hosts="${hosts}|physix68.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix69.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix70.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix71.ipr.univ-rennes1.fr"
			num_cores='16'
			;;
		'intel_xeon_e5-2660v2')
			hosts="${hosts}physix72.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix73.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix74.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix75.ipr.univ-rennes1.fr"

			hosts="${hosts}|physix76.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix77.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix78.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix79.ipr.univ-rennes1.fr"

			hosts="${hosts}|physix80.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix81.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix82.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix84.ipr.univ-rennes1.fr"
			num_cores='20'
			;;
		'intel_xeon_e5-2660v4')
			hosts="${hosts}physix84.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix85.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix86.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix87.ipr.univ-rennes1.fr"
			num_cores='28'
			;;
		'intel_xeon_gold_6140')
			hosts="${hosts}physix88.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix89.ipr.univ-rennes1.fr"
			num_cores='36'
			;;
		'intel_xeon_gold_6154')
			hosts="${hosts}physix90.ipr.univ-rennes1.fr"
			num_cores='72'
			;;
		'intel_xeon_gold_5222')
			hosts="${hosts}physix92.ipr.univ-rennes1.fr"
			num_cores='4'
			;;
		'intel_xeon_gold_6226r')
			hosts="${hosts}physix93.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix94.ipr.univ-rennes1.fr"
			num_cores='32'
			;;
		'intel_xeon_gold_6240r')
			hosts="${hosts}physix99.ipr.univ-rennes1.fr"
			num_cores='48'
			;;
		'intel_xeon_gold_6248r')
			hosts="${hosts}physix95.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix96.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix97.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix98.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix99.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix100.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix101.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix102.ipr.univ-rennes1.fr"
			num_cores='48'
			;;
		'amd_epyc_7282')
			hosts="${hosts}physix12.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix13.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix14.ipr.univ-rennes1.fr"
			hosts="${hosts}|physix15.ipr.univ-rennes1.fr"
			num_cores='32'
			;;
		*)
			error "unhandled host_group_id : ${host_group_id}"
			exit 1
			;;
	esac


	quick_test='arch4_quick'  # about 2s on a core i5 8th generation
	representative_test='nh3h2_qma_long'  # about 10min on a core i5 8th generation
	benchmark_test="${representative_test}"
	case "${benchmark_test}" in
		'arch4_quick')
			ram_per_core='1G'
			;;
		'nh3h2_qma_long')
			ram_per_core='2.8G'  # this was enough on physix48, but maybe we can reduce more
			;;
		*)
			error "unhandled benchmark_test : ${benchmark_test}"
			exit 1
			;;
	esac

	git_repos_url="https://github.com/hibridon/hibridon"
	git_user='g-raffy'  # os.environ['HIBRIDON_REPOS_USER']
	git_pass_file="$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat"
	cmake_options=''
	cmake_options="${cmake_options} -DCMAKE_BUILD_TYPE=Release"  # build in release mode for highest performance
	cmake_options="${cmake_options} -DBUILD_TESTING=ON"  # enable hibridon tests
	
	benchmark_command="ctest --output-on-failure -L ^${benchmark_test}\$"

	local env_vars_bash_commands=''
	case "${compiler_id}" in
		'ifort')
			env_vars_bash_commands='module load compilers/ifort/latest'
			cmake_options="${cmake_options} -DCMAKE_Fortran_COMPILER=ifort"  # use intel fortran compiler
			cmake_options="${cmake_options} -DBLA_VENDOR=Intel10_64lp"  # use 64 bits intel mkl with multithreading 
			;;
		'gfortran')
			env_vars_bash_commands=''
			cmake_options="${cmake_options} -DCMAKE_Fortran_COMPILER=gfortran"  # use gfortran compiler
			;;
		*)
			error "unhandled compiler_id : ${compiler_id}"
			exit 1
			;;
	esac


	local hibench_root_dir="$GLOBAL_WORK_DIR/graffy/hibridon/benchmarks/starbench"
	mkdir -p "${hibench_root_dir}"

	local this_bench_dir="${hibench_root_dir}/${hibridon_version}/${benchmark_test}/${host_group_id}/${compiler_id}"
	mkdir -p "${this_bench_dir}"

	local starbench_job_path="${this_bench_dir}/starbench.job"
	cat $SCRIPT_DIR/starbench-template.job | substitute_TAG_with_FILEcontents '<include:starbench.py>' "$SCRIPT_DIR/starbench.py" > "${starbench_job_path}"
	chmod a+x "${starbench_job_path}"

	command="${starbench_job_path} \"${git_repos_url}\" \"${git_user}\" \"${git_pass_file}\" \"${hibridon_version}\" \"${cmake_options}\" \"${benchmark_command}\" \"${env_vars_bash_commands}\""
	echo "command = $command"
		# eval $command

	pushd "${this_bench_dir}"

		qsub_command="qsub"
		qsub_command="${qsub_command} -pe smp ${num_cores}"
		qsub_command="${qsub_command} -l \"hostname=${hosts}\""
		qsub_command="${qsub_command} -cwd"
		qsub_command="${qsub_command} -m ae"
		qsub_command="${qsub_command} -l mem_available=${ram_per_core}"
		qsub_command="${qsub_command} -j y"  # medge stderr file into stdout file for easier reading of history of events
		qsub_command="${qsub_command} -N hibench_${host_group_id}_${compiler_id}_${hibridon_version}"
		qsub_command="${qsub_command} ${command}"
		# qsub -pe smp "$num_cores" -l "hostname=${hosts}" 
		echo "qsub_command = $qsub_command"
		eval $qsub_command
	popd
}


function launch_perf_jobs()
{
	local hibridon_version="$1" # the version of hibridon to test, in the form of a valid commit number eg 'a3bed1c3ccfbca572003020d3e3d3b1ff3934fad'

	local compilers=''
	compilers="${compilers} gfortran"
	compilers="${compilers} ifort"

	local host_groups=''
	host_groups="${host_groups} intel_xeon_x5550"
	host_groups="${host_groups} intel_xeon_x5650"
	host_groups="${host_groups} intel_xeon_e5-2660"
	host_groups="${host_groups} intel_xeon_e5-2660v2"
	host_groups="${host_groups} intel_xeon_e5-2660v4"
	host_groups="${host_groups} intel_xeon_gold_6140"
	host_groups="${host_groups} intel_xeon_gold_6154"
	host_groups="${host_groups} intel_xeon_gold_5222"
	host_groups="${host_groups} intel_xeon_gold_6226r"
	host_groups="${host_groups} intel_xeon_gold_6240r"
	host_groups="${host_groups} intel_xeon_gold_6248r"
	host_groups="${host_groups} amd_epyc_7282"

	local compiler=''
	local host_group=''
	for compiler in ${compilers}
	do
		for host_group in ${host_groups}
		do
			launch_job_for_host_group "${hibridon_version}" "${host_group}" "${compiler}"
		done
	done

	#launch_job_for_host_group "${hibridon_version}" 'intel_xeon_gold_6140'
}


launch_perf_jobs "${HIBRIDON_VERSION}"
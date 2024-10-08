This example illustrates how `starbench` is used at IPR (Institut de Physique de Rennes) to measure the performance of [hibridon](https://github.com/hibridon/hibridon) on IPR's cluster (`physix`)




usage:

```sh
20241007-15:08:10 graffy@graffy-ws2:~/work/starbench/starbench.git$ rsync --exclude .git --exclude starbench.venv --exclude tmp --exclude usecases/ipr/hibench/results  -va ./ graffy@alambix.ipr.univ-rennes.fr:/opt/ipr/cluster/work.global/graffy/starbench.git/
sending incremental file list

sent 1,416 bytes  received 25 bytes  960.67 bytes/sec
total size is 140,225  speedup is 97.31
last command status : [0]
```

```sh
graffy@alambix-frontal:/opt/ipr/cluster/work.global/graffy/starbench.git/usecases/ipr/hibench$ ./hibenchonphysix.py --commit-id 53894da48505892bfa05693a52312bacb12c70c9 --results-dir $GLOBAL_WORK_DIR/graffy/hibridon/benchmarks/starbench/hibench/$(date --iso=seconds) --arch-regexp 'intel_xeon_x5650' --cmake-path /usr/bin/cmake
```

`hibenchonphysix.py` script launches two `sge` jobs for each machine type in `physix` cluster:
- one job that performs a benchmark of hibridon with `gfortran` compiler
- one job that performs a benchmark of hibridon with `ifort` compiler

When the job successfully completes, it puts the results of the benchmark on `physix`'s global work directory (eg `/opt/ipr/cluster/work.global/graffy/hibridon/benchmarks/starbench/53894da48505892bfa05693a52312bacb12c70c9/nh3h2_qma_long/intel_xeon_x5550/gfortran`)



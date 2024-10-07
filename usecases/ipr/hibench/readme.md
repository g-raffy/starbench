This example illustrates how `starbench` is used at IPR (Institut de Physique de Rennes) to measure the performance of [hibridon](https://github.com/hibridon/hibridon) on IPR's cluster (`physix`)

usage:

```sh
graffy@physix-frontal:/opt/ipr/cluster/work.global/graffy/starbench$ ./hibenchonphysix.py --commit-id 53894da48505892bfa05693a52312bacb12c70c9 --results-dir $GLOBAL_WORK_DIR/graffy/hibridon/benchmarks/starbench/hibench/2024-10-07-16:00:00
```

`hibenchonphysix.py` script launches two `sge` jobs for each machine type in `physix` cluster:
- one job that performs a benchmark of hibridon with `gfortran` compiler
- one job that performs a benchmark of hibridon with `ifort` compiler

When the job successfully completes, it puts the results of the benchmark on `physix`'s global work directory (eg `/opt/ipr/cluster/work.global/graffy/hibridon/benchmarks/starbench/53894da48505892bfa05693a52312bacb12c70c9/nh3h2_qma_long/intel_xeon_x5550/gfortran`)



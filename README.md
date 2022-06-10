# starbench
a tool to benchmark a git cmake application using embarassingly parallel runs

`starbench` is a tool designed to build and test the performance of an application versioned in a `git` repository and using the `cmake` build system.

In order to measure the performance of the code in *hpc* (high performance computing) environment, `starbench` is designed to make all the cores busy. For this, it uses the same technique as in `hpl`'s `stardgemm` test (that's where the 'star' prefix comes from): the same code is run on each `CPU` core. This way, we performances measures are expected to be more realistic, as the cores won't benefit from the unrealistic boost provided by the memory cache of unued cores.

If the user provides:
- the `url` of the repository
- the commit number of the version to test
- the number of cores the benchmark should use (usually the number of cores of the machine that executes the benchmark)
- the benchmark command to use

then `starbench` will do the rest:
1. clone the repository to a temporary location
2. checkout the requested version
3. configure the build
4. build the code
5. run the becnhmark command for each core
6. output the average duration of the benchmark

## example

```sh
starbench.py --git-repos-url https://github.com/hibridon/hibridon --code-version a3bed1c3ccfbca572003020d3e3d3b1ff3934fad --git-user g-raffy --git-pass-file "$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat" --num-cores 2 --output-dir=/tmp/hibench --cmake-path=/opt/cmake/cmake-3.23.0/bin/cmake --cmake-option=-DCMAKE_BUILD_TYPE=Release --cmake-option=-DBUILD_TESTING=ON --benchmark-command='ctest --output-on-failure -L ^arch4_quick$'
```

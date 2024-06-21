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
bob@bob-ws2:~/work/starbench$ python3 -m venv ./starbench.venv
bob@bob-ws2:~/work/starbench$ source ./starbench.venv/bin/activate
bob@bob-ws2:~/work/starbench$ pip install wheel
Collecting wheel
  Using cached wheel-0.43.0-py3-none-any.whl (65 kB)
Installing collected packages: wheel
Successfully installed wheel-0.43.0
bob@bob-ws2:~/work/starbench$ pip install ./starbench.git
Processing ./starbench.git
  Installing build dependencies ... done
  WARNING: Missing build requirements in pyproject.toml for file:///home/bob/work/starbench/starbench.git.
  WARNING: The project does not specify a build backend, and pip cannot fall back to setuptools without 'wheel'.
  Getting requirements to build wheel ... done
    Preparing wheel metadata ... done
Building wheels for collected packages: starbench
  Building wheel for starbench (PEP 517) ... done
  Created wheel for starbench: filename=starbench-1.0.0-py3-none-any.whl size=8011 sha256=a98c590fbc481722aed3512ae6345cce741615a17c24e67dc88070f85b616c4c
  Stored in directory: /tmp/pip-ephem-wheel-cache-m_0xpm10/wheels/67/41/37/debf4c9251b719f84456398e144dffaa34d18ab336b529dc53
Successfully built starbench
Installing collected packages: starbench
Successfully installed starbench-1.0.0
bob@bob-ws2:~/work/starbench$ starbench --git-repos-url https://github.com/hibridon/hibridon --code-version a3bed1c3ccfbca572003020d3e3d3b1ff3934fad --git-user g-raffy --git-pass-file "$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat" --num-cores 2 --output-dir=/tmp/hibench --cmake-path=/opt/cmake/cmake-3.23.0/bin/cmake --cmake-option=-DCMAKE_BUILD_TYPE=Release --cmake-option=-DBUILD_TESTING=ON --benchmark-command='ctest --output-on-failure -L ^arch4_quick$'
```

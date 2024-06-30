import unittest
import logging
from pathlib import Path
# from cocluto import ClusterController
from starbench.main import starbench_cmake_app, ExistingDir


class StarbenchTestCase(unittest.TestCase):

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def setUp(self) -> None:
        return super().setUp()

    def test_mamul1_benchmark(self):
        logging.info('test_mamul1_benchmark')
        source_code_provider = ExistingDir(Path('/home/graffy/work/starbench/starbench.git/test/mamul1'))
        tmp_dir = Path('tmp').absolute()
        benchmark_command = ['./mamul1', '3000', '10']
        starbench_cmake_app(source_code_provider=source_code_provider, tmp_dir=tmp_dir, num_cores=2, benchmark_command=benchmark_command)
        # self.assertIsInstance(job_state, JobsState)


if __name__ == '__main__':
    unittest.main()
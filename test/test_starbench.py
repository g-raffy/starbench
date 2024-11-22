import unittest
import logging
from pathlib import Path
# from cocluto import ClusterController
from starbench.main import starbench_cmake_app
from starbench.existingdir import ExistingDir


class StarbenchTestCase(unittest.TestCase):
    def setUp(self) -> None:  # pylint: disable=useless-parent-delegation
        return super().setUp()

    def test_mamul1_benchmark(self):
        logging.info('test_mamul1_benchmark')
        source_code_provider = ExistingDir(Path('test/mamul1').absolute())
        tmp_dir = Path('tmp').absolute()
        benchmark_command = ['./mamul1', '3000', '10']
        output_measurements_file_path = tmp_dir / 'measurements.tsv'
        starbench_cmake_app(source_code_provider=source_code_provider, output_measurements_file_path=output_measurements_file_path, tmp_dir=tmp_dir, num_cores=2, benchmark_command=benchmark_command)
        # self.assertIsInstance(job_state, JobsState)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    unittest.main()

from .core import IFileTreeProvider, IFileTreeProviderCreator, FileTreeProviderParams
from pathlib import Path

GitCommitId = str


class ExistingDir(IFileTreeProvider):
    dir_path: Path

    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def get_source_tree_path(self) -> Path:
        return self.dir_path


class ExistingDirCreator(IFileTreeProviderCreator):

    def __init__(self):
        super().__init__('existing-dir')

    def create_tree_creator(self, params: FileTreeProviderParams) -> IFileTreeProvider:
        dir_path = params['dir-path']
        return ExistingDir(dir_path)

from .core import IPasswordProvider, IPasswordProviderCreator, PasswordProviderParams
from pathlib import Path


class LocalFilePP(IPasswordProvider):
    """ password provider where the password is stored in a file
    """
    password_file_path: Path  # the path that stores the password in clear (expected to be readable only by its owner for security reasons). Eg "$HOME/.github/personal_access_tokens/bench.hibridon.cluster.ipr.univ-rennes1.fr.pat"

    def __init__(self, password_file_path: Path):
        super().__init__()
        self.password_file_path = password_file_path

    def get_password(self) -> str:
        with open(self.password_file_path, 'rt', encoding='utf8') as file:
            password = file.readlines()
        num_lines = len(password)
        assert num_lines == 1, f'{self.password_file_path} is expected to contain one line exactly, but it contains {num_lines} line(s).'
        return password[0]


class LocalFilePPCreator(IPasswordProviderCreator):

    def __init__(self):
        super().__init__('password-file')

    def create_password_provider(self, params: PasswordProviderParams) -> IPasswordProvider:
        password_file_path = params['password-file-path']
        return LocalFilePP(password_file_path)

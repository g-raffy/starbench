"""
    parser.add_argument('--git-repos-url', required=True, help='the url of the code to benchmark (eg https://github.com/hibridon/hibridon)')
    parser.add_argument('--code-version', help='the version of the code to use; either a branch or a commit id (eg a3bed1c3ccfbca572003020d3e3d3b1ff3934fad)')
    parser.add_argument('--git-user', help='the git user to use to clone the code repository')
    password_group = parser.add_mutually_exclusive_group()
    password_group.add_argument('--git-pass-file', help='the path to a file containing the password (or personal access token)')
    password_group.add_argument('--git-pass', type=str, help='the password (or personal access token) to use (not recommended for security reasons)')
"""
from typing import Optional
from .core import IFileTreeProvider, IFileTreeProviderCreator, IPasswordProvider, Url, UserId, FileTreeProviderParams, PasswordProviderFactory
import subprocess
from pathlib import Path

GitCommitId = str


class GitCloner(IFileTreeProvider):
    repos_url: Url
    code_version: GitCommitId
    git_user: Optional[UserId]
    password_provider: Optional[IPasswordProvider]
    src_dir: Path  # the temporary directory used to populate the source code

    def __init__(self, repos_url: Url, src_dir: Path, code_version: GitCommitId, git_user: UserId = None, password_provider: IPasswordProvider = None):
        self.repos_url = repos_url
        self.code_version = code_version
        self.git_user = git_user
        self.password_provider = password_provider
        self.src_dir = src_dir

    def get_source_tree_path(self) -> Path:
        self.src_dir.mkdir(exist_ok=True, parents=True)
        git_credentials = []
        if self.git_user:
            git_credentials.append(self.git_user)
        if self.password_provider:
            git_credentials.append(self.password_provider.get_password())
        git_repos_url = self.repos_url
        if len(git_credentials) != 0:
            git_repos_url = git_repos_url.replace('https://', f"https://{':'.join(git_credentials)}@")
        # src_dir.mkdir(exist_ok=True)
        subprocess.run(['git', 'clone', f'{str(self.repos_url)}', str(self.src_dir)], cwd=str(self.src_dir), check=True)
        if self.code_version:
            subprocess.run(['git', 'checkout', f'{self.code_version}'], cwd=str(self.src_dir), check=True)
        return self.src_dir


class GitClonerCreator(IFileTreeProviderCreator):

    def __init__(self):
        super().__init__('git-cloner')

    def create_tree_creator(self, params: FileTreeProviderParams) -> IFileTreeProvider:
        repos_url = params['repos-url']
        code_version = params.get('code-version')
        git_user = params.get('git-user')
        password_provider_params = params['password-provider']
        password_provider = PasswordProviderFactory().create_password_provider(password_provider_params['type'], password_provider_params)
        src_dir = Path(params['src-dir'])
        return GitCloner(repos_url, src_dir, code_version, git_user, password_provider)

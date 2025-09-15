import os

from conda_build.utils import create_file_with_permissions

SMITHY_CONF = os.path.expanduser('~/.conda-smithy')


def _write_token(name, token):
    path = os.path.join(SMITHY_CONF, name + '.token')
    with create_file_with_permissions(path, 0o600) as fh:
        fh.write(token)


def write_secrets_to_files():
    if not os.path.exists(SMITHY_CONF):
        os.makedirs(SMITHY_CONF, exist_ok=True)

    for token_fname, token_name in [
        ("circle", "CIRCLE_TOKEN"),
        ("azure", "AZURE_TOKEN"),
        ("drone", "DRONE_TOKEN"),
        ("travis", "TRAVIS_TOKEN"),
        ("github", "GITHUB_TOKEN"),
        ("anaconda", "STAGING_BINSTAR_TOKEN"),
    ]:
        if token_name in os.environ:
            _write_token(token_fname, os.environ[token_name])


def split_label_from_channel(channel: str) -> tuple[str, str]:
    if "/label/" in channel:
        return channel.split("/label/", 1)
    return channel, "main"


def parse_filename(filename: str) -> tuple[str, str, str, str]:  
    if filename.endswith(".tar.bz2"):
        basename = filename[:-len(".tar.bz2")]
        extension = "tar.bz2"
    elif filename.endswith(".conda"):
        basename = filename[:-len(".conda")]
        extension = "conda"
    else:
        raise ValueError(f"Unknown extension for {filename}")
    pkg_name, version, build = basename.rsplit("-", 2)
    return pkg_name, version, build, extension

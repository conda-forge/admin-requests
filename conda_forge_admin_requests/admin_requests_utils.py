import os

SMITHY_CONF = os.path.expanduser('~/.conda-smithy')

def _write_token(name, token):
    with open(os.path.join(SMITHY_CONF, name + '.token'), 'w') as fh:
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


import os
import sys
import glob
import requests
import subprocess
import tempfile

SMITHY_CONF = os.path.expanduser('~/.conda-smithy')


def get_token_reset_files():
    return (
        [f for f in glob.glob("token_reset/*") if f != "token_reset/example.txt"]
    )


def feedstock_token_exists(organization, name):
    r = requests.get(
        "https://api.github.com/repos/%s/"
        "feedstock-tokens/contents/tokens/%s.json" % (organization, name),
        headers={"Authorization": "token %s" % os.environ["GITHUB_TOKEN"]},
    )
    if r.status_code != 200:
        return False
    else:
        return True


def write_token(name, token):
    with open(os.path.join(SMITHY_CONF, name + '.token'), 'w') as fh:
        fh.write(token)


def delete_feedstock_token(org, feedstock_name):
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.check_call(
            "git clone https://${GITHUB_TOKEN}@github.com/conda-forge/"
            "feedstock-tokens.git",
            cwd=tmpdir,
            shell=True,
        )

        subprocess.check_call(
            "git remote set-url --push origin "
            "https://${GITHUB_TOKEN}@github.com/conda-forge/"
            "feedstock-tokens.git",
            cwd=os.path.join(tmpdir, "feedstock-tokens"),
            shell=True,
        )

        subprocess.check_call(
            "git rm tokens/%s.json" % feedstock_name,
            cwd=os.path.join(tmpdir, "feedstock-tokens"),
            shell=True,
        )

        subprocess.check_call(
            "git commit --allow-empty -am 'removing token for %s'" % feedstock_name,
            cwd=os.path.join(tmpdir, "feedstock-tokens"),
            shell=True,
        )

        subprocess.check_call(
            "git pull",
            cwd=os.path.join(tmpdir, "feedstock-tokens"),
            shell=True,
        )

        subprocess.check_call(
            "git push",
            cwd=os.path.join(tmpdir, "feedstock-tokens"),
            shell=True,
        )


def reset_feedstock_token(name):
    owner_info = ['--organization', 'conda-forge']

    with tempfile.TemporaryDirectory() as tmpdir:
        feedstock_dir = os.path.join(tmpdir, name + "-feedstock")
        os.makedirs(feedstock_dir)

        if feedstock_token_exists("conda-forge", name + "-feedstock"):
            delete_feedstock_token("conda-forge", name + "-feedstock")

        subprocess.check_call(
            ['conda', 'smithy', 'generate-feedstock-token',
             '--feedstock_directory', feedstock_dir] + owner_info)
        subprocess.check_call(
            ['conda', 'smithy', 'register-feedstock-token',
             '--feedstock_directory', feedstock_dir] + owner_info)

        subprocess.check_call(
            ['conda', 'smithy', 'rotate-binstar-token',
             '--without-appveyor',
             '--token_name', 'STAGING_BINSTAR_TOKEN'],
            cwd=feedstock_dir)


def reset_feedstock_tokens_in_file(token_reset_file):
    pkgs_to_do_again = []
    with open(token_reset_file, "r") as fp:
        for line in fp.readlines():
            line = line.strip()
            if line.startswith("#") or len(line) == 0:
                continue

            try:
                reset_feedstock_token(line)
            except Exception as e:
                print(
                    "failed to reset token for '%s': %s" % (line, repr(e)),
                    flush=True,
                )
                pkgs_to_do_again.append(line)

    if pkgs_to_do_again:
        with open(token_reset_file, "w") as fp:
            fp.write(
                "# token reset failed for these packages - trying again later\n"
            )
            for pkg in pkgs_to_do_again:
                fp.write(pkg + "\n")
        subprocess.check_call(f"git add {token_reset_file}", shell=True)
        subprocess.check_call(
            f"git commit -m 'Keeping {token_reset_file} "
            "after failed token reset'",
            shell=True,
        )
    else:
        subprocess.check_call(f"git rm {token_reset_file}", shell=True)
        subprocess.check_call(
            f"git commit -m 'Remove {token_reset_file} after token reset'",
            shell=True,
        )

    subprocess.check_call("git show", shell=True)


def check_for_feedstocks_in_file(token_reset_file):
    missing_feedstocks = []
    with open(token_reset_file, "r") as fp:
        for line in fp.readlines():
            line = line.strip()
            if line.startswith("#") or len(line) == 0:
                continue

            r = requests.get("https://github.com/conda-forge/%s-feedstock" % line)
            if r.status_code != 200:
                missing_feedstocks.append(line)
    return missing_feedstocks


def main():
    mode = sys.argv[1]

    if mode == "reset":
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
                write_token(token_fname, os.environ[token_name])

    token_reset_files = get_token_reset_files()
    missing_feedstocks = []
    for token_reset_file in token_reset_files:
        print("working on file %s" % token_reset_file, flush=True)
        if mode == "reset":
            reset_feedstock_tokens_in_file(token_reset_file)
        else:
            missing_feedstocks.extend(
                check_for_feedstocks_in_file(token_reset_file)
            )

    if missing_feedstocks:
        raise RuntimeError("feedstocks %s could not be found!" % missing_feedstocks)


if __name__ == "__main__":
    main()

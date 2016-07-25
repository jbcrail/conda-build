from contextlib import contextmanager
import os
import subprocess
import sys
import tarfile

import pytest

# these are here to be imported by other things.  Do not remove.
from conda.compat import StringIO, PY3
from conda.config import subdir

from conda_build.config import Config
from conda_build.scripts import prepend_bin_path

thisdir = os.path.dirname(os.path.realpath(__file__))
metadata_dir = os.path.join(thisdir, "test-recipes/metadata")
fail_dir = os.path.join(thisdir, "test-recipes/fail")


def is_valid_dir(parent_dir, dirname):
    valid = os.path.isdir(os.path.join(parent_dir, dirname))
    valid &= not dirname.startswith("_")
    valid &= ('osx_is_app' != dirname or sys.platform == "darwin")
    return valid


@pytest.fixture
def testing_workdir(tmpdir, request):
    """ Create a workdir in a safe temporary folder; cd into dir above before test, cd out after

    :param tmpdir: py.test fixture, will be injected
    :param request: py.test fixture-related, will be injected (see pytest docs)
    """

    saved_path = os.getcwd()

    tmpdir.chdir()
    workdir = tmpdir.mkdir('mysubdir')

    def return_to_saved_path():
        os.chdir(saved_path)

    request.addfinalizer(return_to_saved_path)

    return str(workdir)


@pytest.fixture
def test_config(testing_workdir, request):
    return Config(croot=testing_workdir, verbose=True)


@pytest.fixture
def testing_env(testing_workdir, request):
    env_path = os.path.join(testing_workdir, 'env')

    subprocess.check_call(['conda', 'create', '-yq', '-p', env_path, 'python'])
    path_backup = os.environ['PATH']
    os.environ['PATH'] = prepend_bin_path(os.environ.copy(), env_path, prepend_prefix=True)['PATH']
    os.chdir(env_path)

    # cleanup is done by just cleaning up the testing_workdir
    def reset_path():
        os.environ['PATH'] = path_backup

    request.addfinalizer(reset_path)
    return env_path


def package_has_file(package_path, file_path):
    try:
        with tarfile.open(package_path) as t:
            try:
                text = t.extractfile(file_path).read()
                return text
            except KeyError:
                return False
            except OSError as e:
                raise RuntimeError("Could not extract %s (%s)" % (package_path, e))
    except tarfile.ReadError:
        raise RuntimeError("Could not extract metadata from %s. "
                           "File probably corrupt." % package_path)

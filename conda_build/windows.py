from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, isfile, join

from conda_build import config
from conda_build import environ
from conda_build import source
from conda_build.utils import _check_call
from conda_build.scripts import BAT_PROXY

from conda.compat import iteritems

try:
    import psutil
except ImportError:
    psutil = None

assert sys.platform == 'win32'


def fix_staged_scripts():
    """
    Fixes scripts which have been installed unix-style to have a .bat
    helper
    """
    scripts_dir = join(config.build_prefix, 'Scripts')
    if not isdir(scripts_dir):
        return
    for fn in os.listdir(scripts_dir):
        # process all the extensionless files
        if not isfile(join(scripts_dir, fn)) or '.' in fn:
            continue

        with open(join(scripts_dir, fn)) as f:
            line = f.readline().lower()
            # If it's a #!python script
            if not (line.startswith('#!') and 'python' in line.lower()):
                continue
            print('Adjusting unix-style #! script %s, '
                  'and adding a .bat file for it' % fn)
            # copy it with a .py extension (skipping that first #! line)
            with open(join(scripts_dir, fn + '-script.py'), 'w') as fo:
                fo.write(f.read())
            # now create the batch file
            with open(join(scripts_dir, fn + '.bat'), 'w') as fo:
                fo.write(BAT_PROXY)

        # remove the original script
        os.remove(join(scripts_dir, fn))


def msvc_env_cmd():
    if config.PY3K:
        vcvarsall = (r'C:\Program Files (x86)\Microsoft Visual Studio 10.0'
                     r'\VC\vcvarsall.bat')
    else:
        vcvarsall = (r'C:\Program Files (x86)\Microsoft Visual Studio 9.0'
                     r'\VC\vcvarsall.bat')

    if not isfile(vcvarsall):
        print("Warning: Couldn't find Visual Studio: %r" % vcvarsall)
        return ''

    return '''\
call "%s" %s
''' % (vcvarsall, {32: 'x86', 64: 'amd64'}[config.ARCH])


def kill_processes():
    if psutil is None:
        return
    for n in psutil.get_pid_list():
        try:
            p = psutil.Process(n)
            if p.name.lower() == 'msbuild.exe':
                print('Terminating:', p.name)
                p.terminate()
        except:
            continue


def build(m):
    env = dict(os.environ)
    env.update(environ.get_dict(m))

    for name in 'BIN', 'INC', 'LIB':
        path = env['LIBRARY_' + name]
        if not isdir(path):
            os.makedirs(path)

    src_dir = source.get_dir()
    bld_bat = join(m.path, 'bld.bat')
    with open(bld_bat) as fi:
        data = fi.read()
    with open(join(src_dir, 'bld.bat'), 'w') as fo:
        fo.write(msvc_env_cmd())
        # more debuggable with echo on
        fo.write('@echo on\n')
        for kv in iteritems(env):
            fo.write('set %s=%s\n' % kv)
        fo.write("REM ===== end generated header =====\n")
        fo.write(data)

    cmd = [os.environ['COMSPEC'], '/c', 'bld.bat']
    _check_call(cmd, cwd=src_dir)
    kill_processes()
    fix_staged_scripts()

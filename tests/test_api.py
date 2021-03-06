#!/usr/bin/env python3
# Copyright 2018,2019 by MPI-SWS and Data-ken Research. Licensed under Apache 2.0. See LICENSE.txt.
"""Test programmatic api
"""

import unittest
import sys
import os
import os.path
from os.path import join
import shutil
import subprocess
import json

TEMPDIR=os.path.abspath(os.path.expanduser(__file__)).replace('.py', '_data')

try:
    import dataworkspaces
except ImportError:
    sys.path.append(os.path.abspath(".."))

from dataworkspaces.utils.git_utils import GIT_EXE_PATH

from dataworkspaces.api import get_resource_info, take_snapshot,\
                               get_snapshot_history, restore


def makefile(relpath, contents):
    with open(join(TEMPDIR, relpath), 'w') as f:
        f.write(contents)

class TestApi(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEMPDIR):
            shutil.rmtree(TEMPDIR)
        os.mkdir(TEMPDIR)
        self._run_dws('init')
        os.mkdir(join(TEMPDIR, 'data'))
        makefile('data/data.csv', 'x,y,z\n1,2,3\n')
        os.mkdir(join(TEMPDIR, 'code'))
        makefile('code/test.py', 'print("This is a test")\n')
        results_dir = join(TEMPDIR, 'results')
        os.mkdir(results_dir)
        self._run_git(['add', 'data/data.csv', 'code/test.py'])
        self._run_dws('add git --role=source-data ./data')
        self._run_dws('add git --role=code ./code')
        self._run_dws('add git --role=results ./results')

    def tearDown(self):
        if os.path.exists(TEMPDIR):
            shutil.rmtree(TEMPDIR)

    def _run_dws(self, argstr, cwd=TEMPDIR):
        cmd = 'dws --batch '+argstr
        print(cmd + ' [' + cwd + ']')
        r = subprocess.run(cmd, shell=True, cwd=cwd)
        r.check_returncode()

    def _run_git(self, git_args, cwd=TEMPDIR):
        args = [GIT_EXE_PATH]+git_args
        print(' '.join(args) + (' [%s]' % cwd))
        r = subprocess.run(args, cwd=cwd)
        r.check_returncode()

    def _assert_contents(self, relpath, contents):
        with open(join(TEMPDIR, relpath), 'r') as f:
            data = f.read()
        self.assertEqual(contents, data,
                         "File contents do not match for %s" % relpath)

    def _write_metrics(self, metrics):
        results_dir = join(TEMPDIR, 'results')
        with open(join(results_dir, 'results.json'), 'w') as f:
            json.dump({'metrics':metrics}, f)

    def test_get_resource_info(self):
        rinfo = get_resource_info(TEMPDIR)
        print(rinfo)
        self.assertEqual(3, len(rinfo))
        self.assertEqual('data', rinfo[0].name)
        self.assertEqual('source-data', rinfo[0].role)
        self.assertEqual('git-subdirectory', rinfo[0].resource_type)
        self.assertTrue(rinfo[0].local_path.endswith('tests/test_api_data/data'))
        self.assertEqual('code', rinfo[1].name)
        self.assertEqual('code', rinfo[1].role)
        self.assertEqual('git-subdirectory', rinfo[1].resource_type)
        self.assertTrue(rinfo[1].local_path.endswith('tests/test_api_data/code'))
        self.assertEqual('results', rinfo[2].name)
        self.assertEqual('results', rinfo[2].role)
        self.assertEqual('git-subdirectory', rinfo[2].resource_type)
        self.assertTrue(rinfo[2].local_path.endswith('tests/test_api_data/results'))


    def test_snapshots(self):
        self._write_metrics({'accuracy':0.95, 'precision':0.8, 'roc':0.8})
        hash1 = take_snapshot(TEMPDIR, tag='V1', message='first snapshot')
        history = get_snapshot_history(TEMPDIR)
        self.assertEqual(1, len(history))
        self.assertEqual(1, history[0].snapshot_number)
        self.assertEqual(hash1, history[0].hashval)
        self.assertEqual(['V1'], history[0].tags)
        self.assertEqual('first snapshot', history[0].message)
        self.assertEqual(0.95, history[0].metrics['accuracy'])
        with open(join(TEMPDIR, 'code/test.py'), 'a') as f:
            f.write('print("Version 2")\n')
        self._write_metrics({'accuracy':0.99})
        hash2 = take_snapshot(TEMPDIR, tag='V2', message='second snapshot')
        history = get_snapshot_history(TEMPDIR)
        self.assertEqual(2, len(history))
        self.assertEqual(2, history[1].snapshot_number)
        self.assertEqual(hash2, history[1].hashval)
        self.assertEqual(['V2'], history[1].tags)
        self.assertEqual('second snapshot', history[1].message)
        self.assertEqual(0.99, history[1].metrics['accuracy'])
        restore('V1', TEMPDIR)
        history = get_snapshot_history(TEMPDIR)
        self.assertEqual(2, len(history))
        self._assert_contents('code/test.py',
                              'print("This is a test")\n')
        restore('V2', TEMPDIR)
        self._assert_contents('code/test.py',
                              'print("This is a test")\nprint("Version 2")\n')





if __name__ == '__main__':
    unittest.main()



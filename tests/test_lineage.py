import unittest
import sys
import os
import os.path
from os.path import dirname, abspath, expanduser, exists, join
import shutil
import subprocess
import json

TEST_DIR=abspath(expanduser(dirname(__file__)))

try:
    import dataworkspaces
except ImportError:
    sys.path.append(os.path.abspath(".."))

from dataworkspaces.utils.subprocess_utils import find_exe
from dataworkspaces.utils.lineage_utils import LineageStoreCurrent, ResourceRef,\
    ResourceLineage
from dataworkspaces.utils.git_utils import GIT_EXE_PATH

TEMPDIR=os.path.abspath(os.path.expanduser(__file__)).replace('.py', '_data')
WS_DIR=join(TEMPDIR, 'workspace')
CODE_DIR=join(WS_DIR, 'code')
WS_ORIGIN=join(TEMPDIR, 'workspace_origin.git')


class TestLineage(unittest.TestCase):
    def setUp(self):
        if exists(TEMPDIR):
            shutil.rmtree(TEMPDIR)
        os.mkdir(TEMPDIR)
        os.mkdir(WS_DIR)
        self.dws=find_exe("dws", "Make sure you have enabled your python virtual environment")
        self._run_dws(['init', '--hostname', 'test-host',
                       '--create-resources=code,source-data,intermediate-data,results'],
                      verbose=False)
        with open(join(WS_DIR, 'source-data/data.csv'), 'w') as f:
            f.write('a,b,c\n')
            f.write('1,2,3\n')
        shutil.copyfile(join(TEST_DIR, 'lineage_step1.py'),
                        join(CODE_DIR, 'lineage_step1.py'))
        shutil.copyfile(join(TEST_DIR, 'lineage_step2.py'),
                        join(CODE_DIR, 'lineage_step2.py'))

    def _run_dws(self, dws_args, cwd=WS_DIR, env=None, verbose=True):
        if verbose:
            command = self.dws + ' --verbose --batch '+ ' '.join(dws_args)
        else:
            command = self.dws + ' --batch '+ ' '.join(dws_args)
        print(command + (' [%s]' % cwd))
        r = subprocess.run(command, cwd=cwd, shell=True, env=env)
        r.check_returncode()

    def _run_step(self, script_name, args):
        command = [sys.executable, join(CODE_DIR, script_name)]+args
        print(" ".join(command))
        r = subprocess.run(command, cwd=WS_DIR, shell=False)
        r.check_returncode()

    def tearDown(self):
        if exists(TEMPDIR):
            shutil.rmtree(TEMPDIR)

    def _validate_test_case_file(self, expected_contents, resource_dir):
        with open(join(join(WS_DIR, resource_dir), 'test_case.txt'), 'r') as f:
            data = f.read()
        self.assertEqual(expected_contents, data)

    def _validate_store(self, resources=[ResourceRef('results')],
                        verify_no_placeholders=False):
        store = LineageStoreCurrent.load(join(WS_DIR, '.dataworkspace/current_lineage'))
        warnings = store.validate(resources, verify_no_placeholders=verify_no_placeholders)
        self.assertEqual(0, warnings)

    def _run_git(self, git_args, cwd=WS_DIR):
        args = [GIT_EXE_PATH]+git_args
        print(' '.join(args) + (' [%s]' % cwd))
        r = subprocess.run(args, cwd=cwd)
        r.check_returncode()

    def _check_lineage_files(self, should_be_present, should_not_be_present):
        for r in should_be_present:
            f = join(WS_DIR, '.dataworkspace/current_lineage/%s.json' % r)
            self.assertTrue(exists(f), "Missing expected resource file %s" % f)
        for r in should_not_be_present:
            f = join(WS_DIR, '.dataworkspace/current_lineage/%s.json' % r)
            self.assertFalse(exists(f), "Resource file %s exists, but should not be present" % f)

    def _check_results_lineage(self, snapshot_tag, expected_num_lineages):
        fpath = join(WS_DIR, 'results/snapshots/test-host-%s/lineage.json' % snapshot_tag)
        self.assertTrue(exists(fpath), "%s does not exist" % fpath)
        with open(fpath, 'r') as f:
            data = json.load(f)
        lineages = [ResourceLineage.from_json(r, filename=fpath) for r in data['lineages']]
        self.assertEqual(expected_num_lineages, len(lineages))

    def test_lineage(self):
        self._run_step('lineage_step1.py', ['test_lineage1'])
        self._run_step('lineage_step2.py', ['test_lineage1'])
        self._validate_test_case_file('test_lineage1', 'intermediate-data/s1')
        self._validate_test_case_file('test_lineage1', 'results')
        self._validate_store()
        self._run_dws(['snapshot', 'S1'])
        self._check_results_lineage('S1', 3)
        # we don't verify from the results resource as we've already moved
        # the results as a part of the snapshot
        self._validate_store([ResourceRef('intermediate-data', 's1')],
                             verify_no_placeholders=True)

        self._run_step('lineage_step1.py', ['test_lineage2'])
        self._run_step('lineage_step2.py', ['test_lineage2'])
        self._validate_test_case_file('test_lineage2', 'intermediate-data/s1')
        self._validate_test_case_file('test_lineage2', 'results')

        self._validate_store()
        self._run_dws(['snapshot', 'S2'])
        self._check_results_lineage('S2', 3)

        self._run_dws(['restore', 'S1'])
        self._validate_test_case_file('test_lineage1', 'intermediate-data/s1')
        self._validate_store(resources=[ResourceRef('intermediate-data', 's1')],
                             verify_no_placeholders=True)

    def test_pull(self):
        """Pull should invalidate the current resources
        """
        self._run_git(['init', '--bare', 'workspace_origin.git'],
                      cwd=TEMPDIR)
        self._run_git(['remote', 'add', 'origin', WS_ORIGIN], cwd=WS_DIR)

        self._run_step('lineage_step1.py', ['test_lineage1'])
        self._run_step('lineage_step2.py', ['test_lineage1'])
        self._run_dws(['snapshot', 'S1'])
        self._run_dws(['push'])
        self._check_lineage_files(['source-data', 'intermediate-data'], ['results'])

        self._run_dws(['pull'])
        self._check_lineage_files([], ['source-data', 'intermediate-data', 'results'])

        self._run_dws(['restore', 'S1'])
        self._check_lineage_files(['source-data', 'intermediate-data'], ['results'])


if __name__ == '__main__':
    unittest.main()

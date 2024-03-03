#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE_CMD = sys.executable + ' ' + os.path.abspath('./bin/cmakelint ')

CMAKELISTS = "CMakeLists.txt"


def RunShellCommand(cmd, cwd='.'):
    """
    executes a command
    :param cmd: A string to execute.
    :param cwd: from which folder to run.
    """

    stdout_target = subprocess.PIPE
    stderr_target = subprocess.PIPE

    proc = subprocess.Popen(cmd,
                            shell=True,
                            cwd=cwd,
                            stdout=stdout_target,
                            stderr=stderr_target)
    out, err = proc.communicate()
    # print(err) # to get the output at time of test
    return (proc.returncode, out, err)


class UsageTest(unittest.TestCase):

    def testHelp(self):
        (status, out, err) = RunShellCommand(BASE_CMD + ' --help')
        self.assertEqual(32, status)
        self.assertEqual(b'', out)
        self.assertTrue(err.startswith(b'\nSyntax: cmakelint.py'), err)


class TemporaryFolderClassSetup(object):
    """
    Regression tests: The test starts a filetreewalker scanning for files name *.def
    Such files are expected to have as first line the argument
    to a cpplint invocation from within the same directory, as second line the
    expected status code, and all other lines the expected systemerr output (two blank
    lines at end).
    """
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        """setup tmp folder for testing with samples and custom additions by subclasses"""
        try:
            cls._root = tempfile.mkdtemp()
            shutil.copytree('samples', os.path.join(cls._root, 'samples'))
            cls.prepare_directory(cls._root)
        except Exception:
            try:
                cls.tearDownClass()
            except Exception:
                pass
            raise

    @classmethod
    def tearDownClass(cls):
        if (cls._root):
            # pass
            shutil.rmtree(cls._root)

    @classmethod
    def prepare_directory(cls, root):
        """Override in subclass to manipulate temporary samples root folder before tests"""
        pass

    def checkAllInFolder(self, foldername, expectedDefs):
        # uncomment to show complete diff
        # self.maxDiff = None
        count = 0
        for dirpath, _, fnames in os.walk(foldername):
            for f in fnames:
                if f.endswith('.def'):
                    count += 1
                    self._checkDef(os.path.join(dirpath, f))
        self.assertEqual(count, expectedDefs)

    def _checkDef(self, path):
        """runs command and compares to expected output from def file"""
        # self.maxDiff = None # to see full diff
        with open(path, 'rb') as filehandle:
            datalines = filehandle.readlines()
            stdoutLines = int(datalines[2])
            self._runAndCheck(rel_cwd=os.path.dirname(path),
                              args=datalines[0].decode('utf8').strip(),
                              expectedStatus=int(datalines[1]),
                              expectedOut=[line.decode('utf8').strip(
                              ) for line in datalines[3:3 + stdoutLines]],
                              expectedErr=[line.decode('utf8').strip() for line in datalines[3 + stdoutLines:]])

    def _runAndCheck(self, rel_cwd, args, expectedStatus, expectedOut, expectedErr):
        cmd = BASE_CMD + args
        cwd = os.path.join(self._root, rel_cwd)
        # command to reproduce
        print("\ncd " + cwd + " && " + cmd + " 2> <filename>")
        (status, out, err) = RunShellCommand(cmd, cwd)
        try:
            # print(out.decode('utf8'))
            # print(err.decode('utf8'))
            self.assertEqual(expectedStatus, status,
                             'bad command status %s' % status)
            self.assertEqual(len(expectedErr), len(
                err.decode('utf8').split('\n')))
            self.assertEqual(expectedErr, err.decode('utf8').split('\n'))
            self.assertEqual(len(expectedOut), len(
                out.decode('utf8').split('\n')))
            self.assertEqual(expectedOut, out.decode('utf8').split('\n'))
        except AssertionError as e:
            e.args += ('Failed check in %s for command: %s' % (cwd, cmd),)
            raise e


class RegressionTests(TemporaryFolderClassSetup, unittest.TestCase):

    def test_blender_samples(self):
        self.checkAllInFolder('samples/blender', 2)

    def test_opencv_samples(self):
        self.checkAllInFolder('samples/opencv', 1)

    def test_llvm_samples(self):
        self.checkAllInFolder('samples/llvm', 2)


class SimpleCMakeListsTxt(TemporaryFolderClassSetup, unittest.TestCase):
    """runs in a temporary folder a simple file"""

    @classmethod
    def prepare_directory(cls, root):
        with open(os.path.join(root, CMAKELISTS), 'a'):
            pass

    def test_invocation(self):
        self._runAndCheck('', CMAKELISTS, 0, [""], ["Total Errors: 0", ""])


if __name__ == '__main__':
    unittest.main()

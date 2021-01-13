#! /usr/bin/env python

import imp

from setuptools import setup


def get_version():
    ver_file = None
    try:
        ver_file, pathname, description = imp.find_module(
            '__version__', ['cmakelint'])
        vermod = imp.load_module(
            '__version__', ver_file, pathname, description)
        version = vermod.VERSION
        return version
    finally:
        if ver_file is not None:
            ver_file.close()


def read_without_comments(filename):
    """some pip versions bark on comments (e.g. on travis)"""
    with open(filename) as f:
        return [line for line in f.read().splitlines() if not len(line) == 0 and not line.startswith('#')]


test_required = read_without_comments('test-requirements')

setup(name='cmakelint',
      version=get_version(),
      packages=['cmakelint'],
      scripts=['bin/cmakelint'],
      entry_points={
          'console_scripts': [
              'cmakelint = cmakelint.main:main'
          ]
      },
      install_requires=[],
      setup_requires=[
          "pytest-runner"
      ],
      tests_require=test_required,
      # extras_require allow pip install .[dev]
      extras_require={
          'test': test_required,
          'dev': read_without_comments('dev-requirements') + test_required
      },
      author="Richard Quirk",
      author_email="richard.quirk@gmail.com",
      url="https://github.com/cmake-lint/cmake-lint",
      download_url="https://github.com/cmake-lint/cmake-lint",
      keywords=["cmake", "lint"],
      classifiers=[
        "Topic :: Software Development",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Programming Language :: Other",
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License"],
      description="Static code checker for CMake files",
      long_description=open('README.md').read(),
      long_description_content_type="text/markdown",
      license="Apache 2.0"
      )

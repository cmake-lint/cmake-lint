#! /usr/bin/env python

from setuptools import setup

import imp


def get_version():
    ver_file = None
    try:
        ver_file, pathname, description = imp.find_module('__version__', ['cmakelint'])
        vermod = imp.load_module('__version__', ver_file, pathname, description)
        version = vermod.VERSION
        return version
    finally:
        if ver_file is not None:
            ver_file.close()


with open('requirements-test.txt') as f:
    required = f.read().splitlines()

setup(name='cmakelint',
      version=get_version(),
      packages=['cmakelint'],
      scripts=['bin/cmakelint'],
      entry_points={
          'console_scripts': [
              'cmakelint = cmakelint.main:main'
          ]
      },
      install_requires=[''],
      tests_require=required,
      author="Richard Quirk",
      author_email="richard.quirk@gmail.com",
      url="https://github.com/cmake-lint/cmake-lint",
      download_url="https://github.com/cmake-lint/cmake-lint",
      keywords=["cmake", "lint"],
      classifiers=[
        "Topic :: Software Development",
        "Programming Language :: Other",
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License"],
      description="Static code checker for CMake files",
      long_description="""cmakelint parses CMake files and reports style issues.""",
      license="Apache 2.0"
)

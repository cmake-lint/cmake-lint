Contributing guide
==================

Thanks for your interest in contributing to cmakelint.

Any kinds of contributions are welcome: Bug reports, Documentation, Patches.

Development
-----------

For many tasks, it is okay to just develop using a single installed python version. But if you need to test/debug the project in multiple python versions, you need to install those version:

1. (Optional) Install multiple python versions 
   1. (Optional) Install [pyenv](https://github.com/pyenv/pyenv-installer) to manage python versions
   2. (Optional) Using pyenv, install the python versions used in testing

      pyenv install 2.7.16
      pyenv install 3.6.8
      # ...
      pyenv local 2.7.16 3.6.8 ...

It may be okay to run and test python against locally installed libraries, but if you need to have a consistent build, it is recommended to manage your environment using virtualenv: [virtualenv](https://virtualenv.pypa.io/en/latest/ ), [virtualenv](https://pypi.org/project/virtualenvwrapper/ )

1. (Optional) Setup a local virtual environment with all necessary tools and libraries
     mkvirtualenv cmakelint
     pip install .[dev]
      
You can setup your local environment for developing patches for cmakelint like this:

.. code-block:: bash

    # install cmakelint locally to run against projects
    pip install --user -e .[dev]

    # run tests
    pytest
    ruff check .
    ./tox    # the above in all python environments

Releasing
---------

To release a new version:

.. code-block:: bash

    # prepare files for release
    git checkout develop
    vi cmakelint/__version__py # increment the version
    vi CHANGELOG.md # log changes
    git add cmakelint/__version__py CHANGELOG.md
    git commit -m "Releasing x.y.z"
    # test-release (on env by mkvirtualenv -p /usr/bin/python3)
    pip install --upgrade setuptools wheel twine
    rm -rf dist
    python3 setup.py sdist bdist_wheel
    twine upload --repository testpypi dist/*
    # ... Check website and downloads from https://test.pypi.org/project/cmakelint/
    # Actual release
    git checkout master
    git merge develop
    python3 setup.py sdist bdist_wheel
    twine upload dist/*
    git tag x.y.z
    git push origin master develop --tags

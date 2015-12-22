import re
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


INIT_FILE = 'bettertimedelta/__init__.py'
init_data = open(INIT_FILE).read()

metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", init_data))

AUTHOR_EMAIL = metadata['author']
VERSION = metadata['version']
LICENSE = metadata['license']
DESCRIPTION = metadata['description']

AUTHOR, EMAIL = re.match(r'(.*) <(.*)>', AUTHOR_EMAIL).groups()

requires = ['represent>=1.3.0']
extras_require = {
    'test': ['hypothesis', 'ipython', 'pytest']
}


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

setup(
    name='BetterTimeDelta',
    version=VERSION,
    description=DESCRIPTION,
    # long_description=open('README').read(),
    author=AUTHOR,
    author_email=EMAIL,
    url='https://github.com/RazerM/bettertimedelta',
    packages=find_packages(),
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    license=LICENSE,
    install_requires=requires,
    extras_require=extras_require)

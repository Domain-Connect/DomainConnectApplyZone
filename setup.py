#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import os

from distutils.cmd import Command
from setuptools import setup, find_packages

# ----------------------------------------
# Description
# ----------------------------------------
DESCRIPTION = 'Domain Connect Zone Utility'
LONG_DESCRIPTION = DESCRIPTION
LONG_DESCRIPTION_CONTENT_TYPE = ''
# Place contents of README into 'LONG_DESCRIPTION' for display on pypi.org project page.
here = os.path.abspath(os.path.dirname(__file__))
try:
        with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
                    LONG_DESCRIPTION = '\n' + f.read()
        LONG_DESCRIPTION_CONTENT_TYPE = 'text/plain',
except IOError:
        pass

# ----------------------------------------
# Clean
# ----------------------------------------
class CleanCommand(Command):
    description = "A better cleaner."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        cmd_list = dict(
            build="rm -rf .eggs .pytest_cache dist *.egg-info",
            DS_Store="find ./ -name .DS_Store -delete;",
            pyc="find ./ -name '*.pyc' -delete;",
            empty_dirs="find ./ -type d -empty -delete;"
        )

        for key, cmd in cmd_list.items():
            os.system(cmd)


setup(
    name='domainconnectzone',
    version='4.0.0',
    description=DESCRIPTION,
    author='domainconnect.org',
    url='https://github.com/Domain-Connect/domainconnectzone',
    long_description=LONG_DESCRIPTION,
    packages=find_packages(exclude=["test", "test.*"]),
    install_requires=[
        'ipy>=1.1',
        'six>=1.16.0',
    ],
    extras_require={
        'testing': [
            'coverage>=5.5',
            'pytest>=4.6; python_version == "2.7"',
            'pytest>=7.0; python_version > "2.7"',
            'mock>=3.0.5; python_version < "3.3"',
        ],
        ':python_version == "2.7"': [
            'cryptography>=3.3.2',
            'dnspython>=1.16.0',
            'jsonschema>=3.2.0',
            'requests>=2.27.1',
            'validators>=0.14.2',
        ],
        ':python_version > "2.7" and python_version < "3.6"': [
            'cryptography>=39.0.1',
            'dnspython3>=1.15.0',
            'jsonschema>=4.0.0',
            'requests>=2.27.1',
            'validators>=0.20.0',
        ],
        ':python_version >= "3.6" and python_version < "3.7"': [
            'cryptography>=40.0.2',
            'dnspython3>=1.15.0',
            'jsonschema>=4.0.0',
            'requests>=2.27.1',
            'validators>=0.20.0',
        ],
        ':python_version >= "3.7"': [
            'cryptography>=42.0.3',
            'dnspython3>=1.15.0',
            'jsonschema>=4.0.0',
            'requests>=2.31.0',
            'validators>=0.20.0',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ]
)

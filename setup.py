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
    version='3.0.2',
    description=DESCRIPTION,
    author='domainconnect.org',
    url='https://github.com/Domain-Connect/domainconnectzone',
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[
        'cryptography>=1.8',
        'dnspython>=1.16',
        'IPy>=1.0'
    ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3"
    ]
)

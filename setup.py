#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from setuptools import setup, find_packages


setup(name='domainconnectzone',
      version='1.0',
      description='Domain Connect Zone Utility',
      author='domainconnect.org',
      url='https://github.com/Domain-Connect/domainconnectzone',
      packages=find_packages(),
      install_requires=[
          'cryptography>=1.8',
          'dnspython>=1.16',
          'IPy>=1.0'
          ],
      classifiers=[
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 3"
      ])

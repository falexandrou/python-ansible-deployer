"""Stackmate Project setup"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pipenv install twine --dev

import io
import os

from setuptools import find_packages, setup

# Package meta-data.
NAME = 'stackmate'
DESCRIPTION = 'Effortless application & infrastructure deployments'
URL = 'https://github.com/stackmate-io/stackmate-cli'
EMAIL = 'fotis@stackmate.io'
AUTHOR = 'Fotis Alexandrou'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = '1.0.0'
LICENSE = 'MIT'

# Packages that are required for this module to be executed
REQUIRED = [
    'ansible==2.9.17',
    'click==7.0',
    'boto3==1.17.14',
    'botocore==1.20.14',
    'boto==2.49.0',
    'Jinja2==2.10.1',
    'dnspython==1.16.0',
    'sendgrid==6.1.1',
    'pathos==0.2.5',
    'PyYAML==5.3.1',
    'requests==2.22.0',
    'urllib3==1.25.8',
    'redis==3.5.3',
]

# Packages that are optional
EXTRAS = {
    'dev': [
        'vcrpy==2.0.1',
        'ansible-lint==4.2.0',
        'expects==0.9.0',
        'doubles==1.5.3',
        'pytest==5.4.1',
        'pytest-asyncio==0.11.0',
        'pytest-describe==0.12.0',
        'pytest-datafiles==2.0',
        'pytest-watch==2.0.0',
        'molecule==2.22',
        'docker==4.4.0',
        'GitPython==3.1.0',
    ],
}

# Import the README and use it as the long-description.
HERE = os.path.abspath(os.path.dirname(__file__))
try:
    with io.open(os.path.join(HERE, 'README.md'), encoding='utf-8') as f:
        LONG_DESCRIPTION = '\n' + f.read()
except FileNotFoundError:
    LONG_DESCRIPTION = DESCRIPTION

# Where the magic happens:
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],
    entry_points={
        'console_scripts': [
            'stackmate=stackmate.__main__:main',
        ],
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license=LICENSE,
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)

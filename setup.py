#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os

from setuptools import setup

with io.open('README.md', 'r') as fh:
    long_description = fh.read()

requirements = [
    'jsonschema>=2.5.1',
    'strict_rfc3339>=0.7',
    'azure-functions==1.0.0b3',
    'werkzeug>=0.14.1',
]

test_requirements = [
    'coverage==4.1',
    'pyyaml==4.2b4',
    'pytest==4.2.1',
    'mock>=2.0.0',
    'prospector==1.1.6.2',
] + requirements

extras = {
    'test': test_requirements
}

metadata = {}
version_filename = os.path.join(os.path.dirname(__file__), 'functionapprest','__version__.py')
exec(open(version_filename).read(), None, metadata)

setup(
    name='functionapprest',
    version=metadata['__version__'],
    description="Micro framework for azure functions with optional json schema validation",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=metadata['__author__'],
    author_email=metadata['__email__'],
    url='https://github.com/eduardomourar/python-functionapprest',
    packages=[
        'functionapprest',
    ],
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords='functionapp azure rest json schema jsonschema',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras
)

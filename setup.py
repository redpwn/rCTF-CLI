#!/usr/bin/env python3

from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='rctf-cli',
    version='1.0',
    description='A CLI tool for managing your rCTF installation',
    license="BSD-3-Clause",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Aaron Esau',
    author_email='redpwn@aaronesau.com',
    url="http://rctf.redpwn.net/",
    packages=['rctf'],
    install_requires=['requests', 'envparse'],
    scripts=[
        'scripts/rctf'
    ],
    python_requires='>=3.6',
)

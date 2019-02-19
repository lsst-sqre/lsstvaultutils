#!/usr/bin/env python
"""Setup Tools Script"""
import io
import os
import codecs
from setuptools import setup, find_packages

PACKAGENAME = 'lsstvaultutils'
DESCRIPTION = 'LSST SQuaRE Vault utilities'
AUTHOR = 'Adam Thornton'
AUTHOR_EMAIL = 'athornton@lsst.org'
URL = 'https://github.com/lsst-sqre/lsstvaultutils'
LICENSE = 'MIT'


def get_version(file, name='__version__'):
    """Get the version of the package from the given file by
    executing it and extracting the given `name`.
    """
    path = os.path.realpath(file)
    version_ns = {}
    with io.open(path, encoding="utf8") as f:
        exec(f.read(), {}, version_ns)
    return version_ns[name]


def local_read(filename):
    """Convenience function for includes"""
    full_filename = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        filename)
    return codecs.open(full_filename, 'r', 'utf-8').read()


long_description = local_read('README.md')


setup(
    name=PACKAGENAME,
    version=get_version("%s/_version.py" % PACKAGENAME),
    description=DESCRIPTION,
    long_description=long_description,
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='lsst',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=[
        'hvac<1.0.0',
        'kubernetes<10.0.0',
        'click<8.0.0'
    ],
    entry_points={
        'console_scripts': [
            'copyk2v = lsstvaultutils.secretcopier:standalonek2v',
            'copyv2k = lsstvaultutils.secretcopier:standalonev2k',
            'tokenadmin = lsstvaultutils.tokenadmin:standalone',
            'vaultrmrf = lsstvaultutils.recursivedeleter:standalone'
        ]
    },
)

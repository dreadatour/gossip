#!/usr/bin/env python
"""
Setup script.
"""
from distutils.core import setup

setup(
    name='gossip',
    version='0.1',
    description='Log files proccessing',
    long_description='Log files proccessing',
    author='Vladimir Rudnyh',
    author_email='rudnyh@corp.mail.ru',
    url='https://github.com/dreadatour/gossip',
    packages=['gossip'],
    scripts=['bin/gossip'],
)

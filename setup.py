#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="ast_pe",
    version="0.1",
    description="Partial evaluation on AST level",
    long_description=open("README.rst").read(),
    url="https://github.com/lopuhin/ast_pe",
    author="Konstantin Lopuhin",
    author_email="kostia.lopuhin@gmail.com",
    packages=find_packages(),
    install_requires=["meta"],
    tests_require=["nose"],
    platforms=["any"],
    keywords="AST partial optimization",
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
    ],
)

#!/usr/bin/python3
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aimslite",
    version="0.0.1",
    author="Jon Hurst",
    author_email="jon.a@hursts.org.uk",
    description="Simple GUI for converting detailed rosters to ical or csv",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JonHurst/aimslite",
    py_modules=['aimslite'],
    install_requires=['aimslib>=0.0.7', 'requests'],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "aimsgui = aimslite:main",
            ]
    },
    python_requires='>=3.7',
)

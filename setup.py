import os
from setuptools import setup

__version__ = "0.1.0"

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md")) as f:
    long_description = f.read()

setup(
    name="milliped",
    packages=["milliped"],
    version=__version__,
    description="Web crawling framework",
    long_description=long_description,
    url="https://github.com/jschnab/milleped",
    author="Jonathan Schnabel",
    author_email="jonathan.schnabel31@gmail.com",
    license="GNU General Public License v3.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.6",
    ],
    python_requires=">=3.6.8",
    keywords="web crawling",
    install_requires=[
        "beautifulsoup4",
        "boto3",
        "requests",
        "selenium",
        "sqlalchemy",
        "stem",
    ]
)

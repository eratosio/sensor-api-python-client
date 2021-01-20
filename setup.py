#!/usr/bin/env python
import re
import os
import uuid
from setuptools import setup, find_packages

src_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "src")

VERSION_FILE = os.path.join(src_path, "senaps_sensor", "__init__.py")
ver_file = open(VERSION_FILE, "rt").read()
VERSION_RE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VERSION_RE, ver_file, re.M)

if mo:
    version = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSION_FILE,))


AUTHOR = "CSIRO Data61"
AUTHOR_EMAIL = "senaps@csiro.au"

setup(name="senaps_sensor",
      version=version,
      description="Senaps Sensor Data API Client",
      license="MIT",
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      maintainer=AUTHOR,
      maintainer_email=AUTHOR_EMAIL,
      url="https://bitbucket.csiro.au/projects/SC/repos/sensor-api-python-client/browse",
      packages=find_packages(where='src', exclude=['tests']),
      package_dir={'': 'src'},
      install_requires=[
          'requests==2.22.0',
          'six>=1.7.3',
          'enum34; python_version < "3.4.0"',
      ],
      keywords="senaps sensor api client library",
      classifiers=[
          'Development Status :: 4 - Beta',
          'Topic :: Software Development :: Libraries',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
      ],
      extras_require={
          'pandas-observation-parser': [
              'pandas>=0.18.1,<=0.25.3'
          ]
      },
      zip_safe=True)

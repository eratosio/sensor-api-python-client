# Senaps data platform v2 API client library.
#
# Originall created by
# Copyright 2016 Ionata Digital
#
# Now maintained as part of Senaps platform by
# Copyright 2018 CSIRO
#
# See LICENSE for details.

"""
Senaps data platform sensor API client library
"""
from __future__ import absolute_import, unicode_literals, print_function
from .api import API

__version__ = '2.1.0'
__author__ = 'CSIRO Data61'
__license__ = 'MIT'

api = API()
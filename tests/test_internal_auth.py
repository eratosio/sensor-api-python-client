# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

from requests import PreparedRequest
from requests.structures import CaseInsensitiveDict

from .config import SensorApiInternalTestCase, username, tape

import unittest
import six
if six.PY3:
    from unittest.case import skip
else:
    from unittest2.case import skip

class TestInternalAuth(SensorApiInternalTestCase):

    def test_consumer_header_exists(self):
        p = PreparedRequest()
        p.headers = CaseInsensitiveDict()
        r = self.api.auth(p)

        expected_header = 'X-Consumer-Custom-ID'
        self.assertIn(expected_header,
                      r.headers.keys(),
                      'Did not find %s in headers, auth must be broken' % expected_header)
        self.assertEqual(username,
                         r.headers['X-Consumer-Custom-ID'],
                         'Header not populated with username correctly.')

"""
MIT License
Copyright (c) 2016 Ionata Digital

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
from __future__ import absolute_import, print_function
from .config import SensorApiTestCase, username, tape

import unittest
import six
if six.PY3:
    from unittest.case import skip
else:
    from unittest2.case import skip

class AuthTestCase(SensorApiTestCase):
    @tape.use_cassette('test_credentials_configured.json')
    def test_credentials_configured(self):
        assert self.api.me.id == username

    @tape.use_cassette('test_roles.json')
    def test_roles(self):
        api_roles = self.api.me.roles
        assert len(api_roles) >= 1 #at least one role

    def test_auth_header_not_unicode(self):

        from requests import PreparedRequest

        from requests.structures import CaseInsensitiveDict

        p = PreparedRequest()
        p.headers = CaseInsensitiveDict()
        r = self.api.auth(p)
        k = r.headers.keys()
        for key in k:
            if key == 'Authorization':
                self.assertTrue(type(key) == str, 'Authorization header is unicode not str. Ensure unicode_literals are not imported.')

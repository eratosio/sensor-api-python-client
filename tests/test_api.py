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
from __future__ import unicode_literals, absolute_import, print_function

import json
import time
import traceback
import sys
import datetime

from senaps_sensor.error import SenapsError
from senaps_sensor.models import Organisation, Group, Platform, Stream, StreamResultType, StreamMetaData, StreamMetaDataType, \
    InterpolationType, Observation, UnivariateResult
from senaps_sensor.utils import SenseTEncoder
from senaps_sensor.binder import bind_api

from tests.config import *
from pprint import pprint

import six
if six.PY3:
    import unittest
    from unittest.case import skip
else:
    import unittest2 as unittest
    from unittest2.case import skip


def dumps(*args, **kwargs):
    if 'cls' not in kwargs:
        kwargs['cls'] = SenseTEncoder
    return json.dumps(*args, **kwargs)


class ApiTestCase(SensorApiTestCase):
    existing_platform_id = '05b31a8b-0549-4484-a1b9-a05b89fc677f'
    new_platform_id = 'bdd78502-11bc-4645-9597-0d3231f27212'
    non_existent_stream_id = '0228cefb-8782-4f99-9492-ad3f1febdc12'
    new_stream_id = '21cdbef1f3da-2949-99f4-2878-bfec8220'

    def setUp(self):
        super(ApiTestCase, self).setUp()

    def generate_platform(self):
        o = Organisation()
        o.id = "sandbox"

        g = Group()
        g.id = "group1"

        p = Platform()
        p.id = "test_platform_{0}".format(self.new_platform_id)
        p.name = "A Platform create for unittests"
        p.organisations = [o]
        p.groups = [g]
        return p

    def generate_geolocation_stream(self, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.geolocation
        sm.interpolation_type = InterpolationType.continuous
        s,p = self._generate_stream(StreamResultType.geolocation, sm, stream_id)

        return s,p

    def generate_scalar_stream(self, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.scalar
        sm.interpolation_type = InterpolationType.continuous
        sm.observed_property = "http://registry.it.csiro.au/def/environment/property/air_temperature"
        sm.unit_of_measure = "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/DegreeCelsius"
        s, p = self._generate_stream(StreamResultType.scalar, sm, stream_id)
        return s, p

    def generate_vector_stream(self, length, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.vector
        sm.length = length
        s, p = self._generate_stream(StreamResultType.vector, sm, stream_id)
        return s, p

    def generate_image_stream(self, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.image

        s, p = self._generate_stream(StreamResultType.image, sm, stream_id)
        return s, p

    def generate_regularly_binned_vector_stream(self, start, end, step, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.regularly_binned_vector
        sm.start = start
        sm.end = end
        sm.step = step

        sm.observed_property = "http://registry.it.csiro.au/def/environment/property/absorption_total"
        sm.amplitude_unit = "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/Percent"
        sm.length_unit = "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/Angstrom"

        s, p = self._generate_stream(StreamResultType.vector, sm, stream_id)
        return s, p

    def generate_group(self, id):

        g = Group()
        g.id = id
        g.name = 'Unit Test Group'

        return g

    def _generate_stream(self, stream_type, stream_meta_data, stream_id=None):
        p = self.generate_platform()

        o = Organisation()
        o.id = p.organisations[0].id

        g = Group()
        g.id = p.groups[0].id

        s = Stream()
        s.id = "{0}_{1}".format(stream_id if stream_id else self.new_stream_id, stream_type.value)

        s.groups = [g]
        s.organisations = [o]

        s.result_type = stream_type

        s.samplePeriod = 'PT10S'
        s.reportingPeriod = 'P1D'

        s.metadata = stream_meta_data

        return s, p

    @tape.use_cassette('test_create_platform.json')
    def test_create_platform(self):
        """
        Platform creation test, no clean up
        :return: None
        """
        # create
        p = self.generate_platform()

        required_json = dumps({
            "id": p.id,
            "name": p.name,
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "streamids": [
            ],
            "deployments": [
            ]
        }, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_json = p.to_json("create")

        # verify json
        self.assertEqual(actual_json, required_json)

        created_platform = self.api.create_platform(p)

        # verify
        self.assertEqual(created_platform.id, p.id)
        self.assertEqual(created_platform.name, p.name)

    @skip("Permissions issues")
    @skip
    def test_update_platform(self):
        """
        Platform update test, no clean ups
        :return: None
        """
        # create
        p = self.generate_platform()
        created_platform = self.api.create_platform(p)

        # update, by appending id to name attr
        created_platform.name += created_platform.id
        updated_platform = self.api.update_platform(created_platform)

        # verify
        self.assertEqual(updated_platform.name, created_platform.name)

    @skip("Permissions issues")
    @skip
    def test_delete_platform(self):
        """
        Platform deletion test, create and cleanup
        :return: None
        """
        # create
        p = self.generate_platform()
        created_platform = self.api.create_platform(p)
        created_platform.name += created_platform.id

        # delete
        deleted_platform = self.api.destroy_platform(created_platform)

        # verify
        self.assertIsNone(deleted_platform)

    @tape.use_cassette('test_verify_init_stream.json')
    @skip
    def test_verify_init_stream(self):
        # required
        stream = {}
        stream['id'] = "{0}_location".format(self.existing_platform_id)
        stream['resulttype'] = 'geolocationvalue'
        stream['groupids'] = ['tourtracker']
        stream['samplePeriod'] = 'PT10S'
        stream['reportingPeriod'] = 'P1D'
        stream['organisationid'] = 'utas'
        stream['streamMetadata'] = {
            # 'type': '.GeoLocationStreamMetaData', # type is not used or returned after creation
            'interpolationType': 'http://www.opengis.net/def/waterml/2.0/interpolationType/Continuous',
        }
        required_json = dumps(stream, sort_keys=True)  # be explict with key order since dumps gives us a string

        # get from api
        s = self.api.get_stream(id=stream['id'])
        actual_json = s.to_json("get")

        # verify json
        self.assertEqual(actual_json, required_json)

    @tape.use_cassette('test_non_existent_stream.json')
    @skip
    def test_non_existent_stream(self):
        stream_nonexistent_id = "{0}_nonexistent".format(self.non_existent_stream_id)
        # stream_exists_id = "{0}_location".format(self.existing_platform_id)

        with self.assertRaises(SenapsError) as arc:
            s = self.api.get_stream(id=stream_nonexistent_id)

        try:
            s = self.api.get_stream(id=stream_nonexistent_id)
        except SenapsError as ex:
            self.assertEqual(ex.api_code, 401)

    @tape.use_cassette('test_create_geolocation_stream.json')
    def test_create_geolocation_stream(self):
        s, p = self.generate_geolocation_stream()

        required_state = {
            "id": s.id,
            "resulttype": "geolocationvalue",
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "samplePeriod": "PT10S",
            "reportingPeriod": 'P1D',
            "streamMetadata": {
                "type": ".GeoLocationStreamMetaData",
                "interpolationType": "http://www.opengis.net/def/waterml/2.0/interpolationType/Continuous",
            }
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = s.to_state("create")
        actual_json = s.to_json("create")

        # dict diff
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(s.id, created_stream.id)

        # verify json
        self.assertEqual(actual_json, required_json)

    @tape.use_cassette('test_create_scalar_stream.json')
    def test_create_scalar_stream(self):
        s, p = self.generate_scalar_stream()

        required_state = {
            "id": s.id,
            "resulttype": "scalarvalue",
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "samplePeriod": "PT10S",
            "reportingPeriod": 'P1D',
            "streamMetadata": {
                "type": ".ScalarStreamMetaData",
                "interpolationType": "http://www.opengis.net/def/waterml/2.0/interpolationType/Continuous",
                "observedProperty":  "http://registry.it.csiro.au/def/environment/property/air_temperature",
                "unitOfMeasure": "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/DegreeCelsius"
            }
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = s.to_state("create")
        actual_json = s.to_json("create")

        # dict diff
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(s.id, created_stream.id)

        # verify json
        self.assertEqual(actual_json, required_json)


    @tape.use_cassette('test_create_vector_stream.json')
    def test_create_vector_stream(self):
        s, p = self.generate_vector_stream(3)

        required_state = {
            "id": s.id,
            "resulttype": "vectorvalue",
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "samplePeriod": "PT10S",
            "reportingPeriod": 'P1D',
            "streamMetadata": {
                "type": ".VectorStreamMetaData",
                "length": 3
            }
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = s.to_state("create")
        actual_json = s.to_json("create")

        # dict diff
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(s.id, created_stream.id)

        # verify json
        self.assertEqual(actual_json, required_json)


    @tape.use_cassette('test_create_regularly_binned_vector_stream.json')
    def test_create_regularly_binned_vector_stream(self):
        s, p = self.generate_regularly_binned_vector_stream(10, 20, 2, "ba94aada-84d0-420c-87d9-5510a17c176d")

        required_state = {
            "id": s.id,
            "resulttype": "vectorvalue",
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "samplePeriod": "PT10S",
            "reportingPeriod": 'P1D',
            "streamMetadata": {
                "type": ".RegularlyBinnedVectorStreamMetaData",
                "start": 10,
                "end": 20,
                "step": 2,
                "observedProperty": "http://registry.it.csiro.au/def/environment/property/absorption_total",
                "amplitudeUnit": "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/Percent",
                "lengthUnit": "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/Angstrom"
            }
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = s.to_state("create")
        actual_json = s.to_json("create")

        # dict diff
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(s.id, created_stream.id)

        # verify json
        self.assertEqual(actual_json, required_json)

    @tape.use_cassette('test_create_image_stream.json')
    def test_create_image_stream(self):
        s, p = self.generate_image_stream("403e2a68-7e4c-43e3-93d4-71d8980014fa")

        required_state = {
            "id": s.id,
            "resulttype": "imagevalue",
            "organisationid": p.organisations[0].id,
            "groupids": [
                p.groups[0].id
            ],
            "samplePeriod": "PT10S",
            "reportingPeriod": 'P1D',
            "streamMetadata": {
                "type": ".ImageStreamMetaData",
            }
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = s.to_state("create")
        actual_json = s.to_json("create")

        # dict diff
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(s.id, created_stream.id)

        # verify json
        self.assertEqual(actual_json, required_json)


    @tape.use_cassette('test_create_geolocation_observations.json')
    def test_create_geolocation_observations(self):
        s, p = self.generate_geolocation_stream()

        o = Observation()

        dt = datetime.datetime(2016, 2, 15, 0, 0, 0)
        dt_td = datetime.timedelta(minutes=15)

        points = [
            {'time': dt + (dt_td * 0), "lng": 147.326262, "lat": -42.8840887, 'alt': 50},
            {'time': dt + (dt_td * 1), "lng": 147.3263529, "lat": -42.8844541},  # altitude missing, just because.
            {'time': dt + (dt_td * 2), "lng": 147.3232176, "lat": -42.883477, 'alt': 250},
        ]

        for p in points:
            item = UnivariateResult()
            item.t = p.get('time')
            coords = [p.get('lng'), p.get('lat'), p.get('alt')] if p.get('alt') is not None else [p.get('lng'), p.get('lat')]

            item.v = {
                'p': {
                    'type': 'Point',
                    'coordinates': coords
                }
            }
            o.results.append(item)

        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        required_state = {
            'results': [
                {
                    't':  points[0].get('time').strftime(dt_format),
                    'v': {
                        'p': {
                            'type': 'Point',
                            'coordinates': [points[0].get('lng'), points[0].get('lat'), points[0].get('alt')]
                        }
                    }
                },
                {
                    't':  points[1].get('time').strftime(dt_format),
                    'v': {
                        'p': {
                            'type': 'Point',
                            'coordinates': [points[1].get('lng'), points[1].get('lat')]
                        }
                    }
                },
                {
                    't':  points[2].get('time').strftime(dt_format),
                    'v': {
                        'p': {
                            'type': 'Point',
                            'coordinates': [points[2].get('lng'), points[2].get('lat'), points[2].get('alt')]
                        }
                    }
                },
            ]
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = o.to_state("create")
        actual_json = o.to_json("create")

        ### dict diff debugging
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        created_stream = self.api.create_stream(s)

        self.assertEqual(created_stream.id, s.id)

        created_observation = self.api.create_observations(o, streamid=s.id)

        self.assertEqual(created_observation.get('message'), "Observations uploaded")
        self.assertEqual(created_observation.get('status'), 201)

    @tape.use_cassette('test_create_scalar_observations.json')
    def test_create_scalar_observations(self):
        s, p = self.generate_scalar_stream()

        o = Observation()

        dt = datetime.datetime(2016, 2, 15, 0, 0, 0)
        dt_td = datetime.timedelta(minutes=15)

        points = [
            {'time': dt + (dt_td * 0), 'v': 1},
            {'time': dt + (dt_td * 1), 'v': 2},
            {'time': dt + (dt_td * 2), 'v': 3},
        ]

        for p in points:
            item = UnivariateResult()
            item.t = p.get('time')
            item.v = {
                'v': p.get('v')
            }
            o.results.append(item)

        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        required_state = {
            'results': [
                {
                    't':  points[0].get('time').strftime(dt_format),
                    'v': {
                        'v': points[0].get('v')
                    }
                },
                {
                    't':  points[1].get('time').strftime(dt_format),
                    'v': {
                        'v': points[1].get('v')
                    }
                },
                {
                    't':  points[2].get('time').strftime(dt_format),
                    'v': {
                        'v': points[2].get('v')
                    }
                },
            ]
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = o.to_state("create")
        actual_json = o.to_json("create")

        ### dict diff debugging
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        print("creating stream %s" % s)
        created_stream = self.api.create_stream(s)

        self.assertEqual(created_stream.id, s.id)

        created_observation = self.api.create_observations(o, streamid=s.id)

        self.assertEqual(created_observation.get('message'), "Observations uploaded")
        self.assertEqual(created_observation.get('status'), 201)

    @tape.use_cassette('test_create_vector_observations.json')
    def test_create_vector_observations(self):
        o = Observation()

        dt = datetime.datetime(2016, 2, 15, 0, 0, 0)
        dt_td = datetime.timedelta(minutes=15)

        points = [1, 2, 3]

        s, p = self.generate_vector_stream(len(points))

        item = UnivariateResult()
        item.t = dt
        item.v = { 'v': points }
        o.results.append(item)

        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        required_state = {
            'results': [
                {
                    't': dt.strftime(dt_format),
                    'v': { 'v': [points[0], points[1], points[2]] }
                },
            ]
        }
        required_json = dumps(required_state,
                              sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = o.to_state("create")
        actual_json = o.to_json("create")

        ### dict diff debugging
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        print("creating stream %s" % s)
        created_stream = self.api.create_stream(s)

        self.assertEqual(created_stream.id, s.id)

        created_observation = self.api.create_observations(o, streamid=s.id)

        self.assertEqual(created_observation.get('message'), "Observations uploaded")
        self.assertEqual(created_observation.get('status'), 201)

    @tape.use_cassette('test_create_regularly_binned_vector_observations.json')
    def test_create_regularly_binned_vector_observations(self):
        o = Observation()

        dt = datetime.datetime(2016, 2, 15, 0, 0, 0)
        dt_td = datetime.timedelta(minutes=15)

        points = [1, 2, 3]

        s, p = self.generate_regularly_binned_vector_stream(1, 3, 1, "a8a8ce25-30f6-4b1a-ac78-533d2887280f")

        item = UnivariateResult()
        item.t = dt
        item.v = { 'v': points }
        o.results.append(item)

        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        required_state = {
            'results': [
                {
                    't': dt.strftime(dt_format),
                    'v': { 'v': [points[0], points[1], points[2]] }
                },
            ]
        }
        required_json = dumps(required_state,
                              sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = o.to_state("create")
        actual_json = o.to_json("create")

        ### dict diff debugging
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        print("creating stream %s" % s)
        created_stream = self.api.create_stream(s)

        self.assertEqual(created_stream.id, s.id)

        created_observation = self.api.create_observations(o, streamid=s.id)

        self.assertEqual(created_observation.get('message'), "Observations uploaded")
        self.assertEqual(created_observation.get('status'), 201)


    @tape.use_cassette('test_create_image_observations.json')
    def test_create_image_observations(self):
        s, p = self.generate_image_stream("13136661-8c66-47c6-9cd1-b74e4214a4ab")

        o = Observation()

        dt = datetime.datetime(2016, 2, 15, 0, 0, 0)
        dt_td = datetime.timedelta(minutes=15)

        points = [
            {'time': dt + (dt_td * 0), 'm': 'image/png', 'd': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='},
            {'time': dt + (dt_td * 1), 'm': 'image/png', 'd': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='},
            {'time': dt + (dt_td * 2), 'm': 'image/png', 'd': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='}
        ]

        for p in points:
            item = UnivariateResult()
            item.t = p.get('time')
            item.v = {
                'm': p.get('m'),
                'd': p.get('d')
            }
            o.results.append(item)

        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        required_state = {
            'results': [
                {
                    't':  points[0].get('time').strftime(dt_format),
                    'v': {
                        'm': points[0].get('m'),
                        'd': points[0].get('d')
                    }
                },
                {
                    't':  points[1].get('time').strftime(dt_format),
                    'v': {
                        'm': points[1].get('m'),
                        'd': points[1].get('d')
                    }
                },
                {
                    't':  points[2].get('time').strftime(dt_format),
                    'v': {
                        'm': points[2].get('m'),
                        'd': points[2].get('d')
                    }
                },
            ]
        }
        required_json = dumps(required_state, sort_keys=True)  # be explict with key order since dumps gives us a string

        actual_state = o.to_state("create")
        actual_json = o.to_json("create")

        ### dict diff debugging
        # from deepdiff import DeepDiff
        # diff = DeepDiff(required_state, actual_state)

        # verify json
        self.assertEqual(actual_json, required_json)

        print("creating stream %s" % s.id)
        created_stream = self.api.create_stream(s)
        print("done creating stream %s")

        self.assertEqual(created_stream.id, s.id)

        print("creating observations %s" % s.id)
        created_observation = self.api.create_observations(o, streamid=s.id)

        print("done creating observations %s" % s.id)
        self.assertEqual(created_observation.get('message'), "Observations uploaded")
        self.assertEqual(created_observation.get('status'), 201)

    @tape.use_cassette('test_connection_timeout.json')
    def test_connection_timeout(self):

        # Override connect timeout to speed this test up a bit
        connect_timeout = 1
        self.api.timeout = (connect_timeout, 3)
        self.api.backoff_factor = 0

        # Set to an invalid IP to force a connect timeout
        self.api.host = '1.2.3.4'

        # Calculate expected time to fail
        expected_time = connect_timeout * (self.api.connect_retries+1)

        t0 = time.time()

        with self.assertRaises(SenapsError):
            self.api.streams()

        t = time.time() - t0
        print('Connect timeout took', t, 'seconds')
        self.assertTrue((expected_time - 0.5) <= t <= (expected_time + 0.5), 'Timeout took %f, expected, %f' % (t, expected_time))

    @tape.use_cassette('test_connection_refused.json')
    def test_connection_refused(self):

        # Set to localhost and closed port to force a connect refused
        self.api.host = 'localhost:700' # hopefully a closed port

        # slow down the backoff, set connect retries
        self.api.backoff_factor = 2
        self.api.connect_retries = 3

        # Calculate expected time to fail
        expected_time = 12 # 0s, 4s, 8s = 12s total

        t0 = time.time()

        with self.assertRaises(SenapsError):
            self.api.streams()

        t = time.time() - t0
        print('Connect timeout took', t, 'seconds')
        self.assertTrue((expected_time - 0.5) <= t <= (expected_time + 0.5),
                        'Timeout took %f, expected, %f' % (t, expected_time))

    @tape.use_cassette('test_bad_gateway.json')
    def test_bad_gateway(self):

        # Set to localhost and closed port to force a connect refused
        self.api.host = 'httpstat.us'  # hopefully a closed port
        self.api.api_root = '/'

        # slow down the backoff, set connect retries
        self.api.backoff_factor = 2
        self.api.status_retries = 3

        # Calculate expected time to fail
        expected_time = 16

        t0 = time.time()

        with self.assertRaises(SenapsError):
            self.r = bind_api(
                api=self.api,
                path='/502', #point us to the httpstat.us test endpoint
                payload_type='json',
                allowed_param=['limit', 'id'],
                query_only_param=[
                    'id',
                    'limit',
                    'skip',
                    'near',
                    'radius',
                    'resulttype',
                    'expand',
                    'recursive',
                    'groupids',
                    'organisationid',
                    'locationid',
                    'usermetadatafield',
                    'usermetadatavalues'
                ],
                payload_list=True,
                require_auth=True,
            )()

        t = time.time() - t0
        print('Connect timeout took', t, 'seconds')
        self.assertTrue((expected_time - 1) <= t <= (expected_time + 1),
                        'Timeout took %f, expected, %f' % (t, expected_time))


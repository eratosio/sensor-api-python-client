"""
MIT License
Copyright (c) 2020 CSIRO

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
import datetime
import uuid

from senaps_sensor.error import SenapsError
from senaps_sensor.models import Deployment, Organisation, Group, Platform, Stream, StreamResultType, StreamMetaData, \
    StreamMetaDataType, \
    InterpolationType, Observation, UnivariateResult, Location, User, Role
import pandas as pd
from pandas.testing import assert_frame_equal
from senaps_sensor.parsers import PandasObservationParser

from senaps_sensor.const import VALID_PROTOCOLS

from senaps_sensor.utils import SenseTEncoder
from senaps_sensor.binder import bind_api

from tests.config import *

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


class ParsersTestCase(SensorApiTestCase):

    def setUp(self):
        super(ParsersTestCase, self).setUp()

    def generate_scalar_stream(self, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.scalar
        sm.interpolation_type = InterpolationType.continuous
        sm.observed_property = "http://registry.it.csiro.au/def/environment/property/air_temperature"
        sm.unit_of_measure = "http://registry.it.csiro.au/def/qudt/1.1/qudt-unit/DegreeCelsius"
        s = self._generate_stream(StreamResultType.scalar, sm, stream_id)
        return s

    def generate_vector_stream(self, length, stream_id=None):
        sm = StreamMetaData()
        sm.type = StreamMetaDataType.vector
        sm.length = length
        s = self._generate_stream(StreamResultType.vector, sm, stream_id)
        return s

    def _generate_stream(self, stream_type, stream_meta_data, stream_id=None):

        o = Organisation()
        o.id = 'sandbox'

        s = Stream()
        s.id = stream_id if stream_id is not None else str(uuid.uuid1())

        s.organisations = [o]

        s.result_type = stream_type

        s.samplePeriod = 'PT10S'
        s.reportingPeriod = 'P1D'

        s.metadata = stream_meta_data

        return s

    def generate_observations(self, basetimestamp=None, deltat=None, obs=None):

        o = Observation()
        if basetimestamp:
            dt = basetimestamp.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = datetime.datetime(2016, 2, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)

        if deltat:
            dt_td = deltat
        else:
            dt_td = datetime.timedelta(minutes=15)

        if obs:
            points = [{'time': dt + (dt_td * index), 'v': val} for index, val in enumerate(obs)]
        else:
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

        df = pd.DataFrame(points)
        df.set_index("time", inplace=True)
        df.index.names = ['timestamp']
        if type(points[0]['v']) is type([]):
            df = pd.DataFrame(df['v'].to_list(), index = df.index, columns=['v[%d]'%i for i in range(len(df['v'][0]))])
        return o, points, df


    @tape.use_cassette('test_pandas_get_observations_single_scalar_stream.json')
    def test_pandas_get_observations_single_scalar_stream(self):
        s = self.generate_scalar_stream()
        o, points, df = self.generate_observations(obs=[1.0,2.0,3.0])

        mapnames={'v': s.id}
        expected_df = df.rename(columns=mapnames)
        print("expceted dataframe")
        print(expected_df)

        print("creating stream and observations %s" % s)
        created_stream = self.api.create_stream(s)
        created_observations = self.api.create_observations(o, streamid=s.id)

        print("getting observations")
        CSVparser = PandasObservationParser()
        retrieived_observations = self.api.get_observations(streamid=s.id, media="csv", parser=CSVparser)
        print(retrieived_observations)

        assert_frame_equal(expected_df, retrieived_observations)

        self.api.destroy_observations(streamid=s.id)
        self.api.destroy_stream(id=s.id)

    @tape.use_cassette('test_pandas_get_observations_two_scalar_stream.json')
    def test_pandas_get_observations_two_scalar_stream(self):
        s1 = self.generate_scalar_stream()
        o1, points1, df1 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 0, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[1.0,2.0,3.0])
        mapnames={'v': s1.id}
        df1 = df1.rename(columns=mapnames)

        s2 = self.generate_scalar_stream()
        o2, points2, df2 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 15, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[1.5,2.5,3.5])
        mapnames={'v': s2.id}
        df2 = df2.rename(columns=mapnames)

        expected_df1 = pd.merge(df1, df2, how="outer", left_index=True, right_index=True)
        expected_df2 = pd.merge(df2, df1, how="outer", left_index=True, right_index=True)
        print("expceted dataframe1")
        print(expected_df1)
        print("expceted dataframe2")
        print(expected_df2)

        print("creating stream and observations %s" % s1)
        created_stream = self.api.create_stream(s1)
        created_observations = self.api.create_observations(o1, streamid=s1.id)

        print("creating stream and observations %s" % s2)
        created_stream = self.api.create_stream(s2)
        created_observations = self.api.create_observations(o2, streamid=s2.id)

        CSVparser = PandasObservationParser()
        print("getting observations stream ordering #1")
        retrieived_observations1 = self.api.get_observations(streamid="%s,%s" % (s1.id,s2.id), media="csv", parser=CSVparser)
        print(retrieived_observations1)
        print("getting observations stream ordering #2")
        retrieived_observations2 = self.api.get_observations(streamid="%s,%s" % (s2.id,s1.id), media="csv", parser=CSVparser)
        print(retrieived_observations2)

        assert_frame_equal(expected_df1, retrieived_observations1)
        assert_frame_equal(expected_df2, retrieived_observations2)

        self.api.destroy_observations(streamid=s1.id)
        self.api.destroy_stream(id=s1.id)
        self.api.destroy_observations(streamid=s2.id)
        self.api.destroy_stream(id=s2.id)

    @tape.use_cassette('test_pandas_get_observations_single_vector_stream.json')
    def test_pandas_get_observations_single_vector_stream(self):
        s = self.generate_vector_stream(3)
        o, points, df = self.generate_observations(obs=[[1.0,2.0,3.0],[1.1,2.1,3.1],[1.2,2.2,3.2]])

        mapnames = {'v[%d]'%i : s.id+'[%d]'%i for i in range(3)}
        expected_df = df.rename(columns=mapnames)
        print("expceted dataframe")
        print(expected_df)

        print("creating stream and observations %s" % s)
        created_stream = self.api.create_stream(s)
        created_observations = self.api.create_observations(o, streamid=s.id)

        print("getting observations")
        CSVparser = PandasObservationParser()
        retrieived_observations = self.api.get_observations(streamid=s.id, media="csv", parser=CSVparser)
        print(retrieived_observations)

        assert_frame_equal(expected_df, retrieived_observations)

        self.api.destroy_observations(streamid=s.id)
        self.api.destroy_stream(id=s.id)

    @tape.use_cassette('test_pandas_get_observations_two_vector_stream.json')
    def test_pandas_get_observations_two_vector_stream(self):
        s1 = self.generate_vector_stream(3)
        o1, points1, df1 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 0, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[[1.0,2.0,3.0],[1.1,2.1,3.1],[1.2,2.2,3.2]])
        mapnames = {'v[%d]'%i : s1.id+'[%d]'%i for i in range(3)}
        df1 = df1.rename(columns=mapnames)

        s2 = self.generate_vector_stream(3)
        o2, points2, df2 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 15, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[[-1.0,-2.0,-3.0],[-1.1,-2.1,-3.1],[-1.2,-2.2,-3.2]])
        mapnames = {'v[%d]'%i : s2.id+'[%d]'%i for i in range(3)}
        df2 = df2.rename(columns=mapnames)

        expected_df1 = pd.merge(df1, df2, how="outer", left_index=True, right_index=True)
        expected_df2 = pd.merge(df2, df1, how="outer", left_index=True, right_index=True)
        print("expceted dataframe1")
        print(expected_df1)
        print("expceted dataframe2")
        print(expected_df2)

        print("creating stream and observations %s" % s1)
        created_stream = self.api.create_stream(s1)
        created_observations = self.api.create_observations(o1, streamid=s1.id)

        print("creating stream and observations %s" % s2)
        created_stream = self.api.create_stream(s2)
        created_observations = self.api.create_observations(o2, streamid=s2.id)

        CSVparser = PandasObservationParser()
        print("getting observations stream ordering #1")
        retrieived_observations1 = self.api.get_observations(streamid="%s,%s" % (s1.id,s2.id), media="csv", parser=CSVparser)
        print(retrieived_observations1)
        print("getting observations stream ordering #2")
        retrieived_observations2 = self.api.get_observations(streamid="%s,%s" % (s2.id,s1.id), media="csv", parser=CSVparser)
        print(retrieived_observations2)

        assert_frame_equal(expected_df1, retrieived_observations1)
        assert_frame_equal(expected_df2, retrieived_observations2)

        self.api.destroy_observations(streamid=s1.id)
        self.api.destroy_stream(id=s1.id)
        self.api.destroy_observations(streamid=s2.id)
        self.api.destroy_stream(id=s2.id)

    @tape.use_cassette('test_pandas_get_observations_scalar_vector_stream.json')
    def test_pandas_get_observations_scalar_vector_stream(self):
        s1 = self.generate_vector_stream(3)
        o1, points1, df1 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 0, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[[1.0,2.0,3.0],[1.1,2.1,3.1],[1.2,2.2,3.2]])
        mapnames = {'v[%d]'%i : s1.id+'[%d]'%i for i in range(3)}
        df1 = df1.rename(columns=mapnames)

        s2 = self.generate_scalar_stream()
        o2, points2, df2 = self.generate_observations(basetimestamp = datetime.datetime(2016, 2, 15, 0, 15, 0, tzinfo=datetime.timezone.utc),
                                                      deltat = datetime.timedelta(minutes=15),
                                                      obs=[1.5,2.5,3.5])
        mapnames={'v': s2.id}
        df2 = df2.rename(columns=mapnames)

        expected_df1 = pd.merge(df1, df2, how="outer", left_index=True, right_index=True)
        expected_df2 = pd.merge(df2, df1, how="outer", left_index=True, right_index=True)
        print("expceted dataframe1")
        print(expected_df1)
        print("expceted dataframe2")
        print(expected_df2)

        print("creating stream and observations %s" % s1)
        created_stream = self.api.create_stream(s1)
        created_observations = self.api.create_observations(o1, streamid=s1.id)

        print("creating stream and observations %s" % s2)
        created_stream = self.api.create_stream(s2)
        created_observations = self.api.create_observations(o2, streamid=s2.id)

        CSVparser = PandasObservationParser()
        print("getting observations stream ordering #1")
        retrieived_observations1 = self.api.get_observations(streamid="%s,%s" % (s1.id,s2.id), media="csv", parser=CSVparser)
        print(retrieived_observations1)
        print("getting observations stream ordering #2")
        retrieived_observations2 = self.api.get_observations(streamid="%s,%s" % (s2.id,s1.id), media="csv", parser=CSVparser)
        print(retrieived_observations2)

        assert_frame_equal(expected_df1, retrieived_observations1)
        assert_frame_equal(expected_df2, retrieived_observations2)

        self.api.destroy_observations(streamid=s1.id)
        self.api.destroy_stream(id=s1.id)
        self.api.destroy_observations(streamid=s2.id)
        self.api.destroy_stream(id=s2.id)

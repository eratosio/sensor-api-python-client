"""
MIT License
Copyright (c) 2016 Ionata Digital
Copyright (c) 2009-2014 Joshua Roesslein

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

import datetime
import enum

from senaps_sensor.error import SenapsError
from senaps_sensor.utils import SenseTEncoder
from senaps_sensor.vocabulary import find_unit_of_measurement, find_observed_property


class StreamResultType(enum.Enum):
    scalar = "scalarvalue"
    geolocation = "geolocationvalue"
    vector = "vectorvalue"
    image = "imagevalue"


class StreamMetaDataType(enum.Enum):
    scalar = ".ScalarStreamMetaData"
    geolocation = ".GeoLocationStreamMetaData"
    vector = ".VectorStreamMetaData"
    regularly_binned_vector = ".RegularlyBinnedVectorStreamMetaData"
    image = ".ImageStreamMetaData"


class InterpolationType(enum.Enum):
    continuous = 'http://www.opengis.net/def/waterml/2.0/interpolationType/Continuous'
    discontinuous = 'http://www.opengis.net/def/waterml/2.0/interpolationType/Discontinuous'
    instant_total = 'http://www.opengis.net/def/waterml/2.0/interpolationType/InstantTotal'
    average_preceding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/AveragePrec'
    max_preceding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/MaxPrec'
    min_preceding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/MinPrec'
    total_preceding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/TotalPrec'
    const_preceding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/ConstPrec'
    average_succeeding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/AverageSucc'
    total_succeeding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/TotalSucc'
    min_succeeding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/MinSucc'
    max_succeeding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/MaxSucc'
    const_succeeding = 'http://www.opengis.net/def/waterml/2.0/interpolationType/ConstSucc'


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""
    def __init__(self, max_id=None, since_id=None):
        super(ResultSet, self).__init__()
        self._max_id = max_id
        self._since_id = since_id

    @property
    def max_id(self):
        if self._max_id:
            return self._max_id
        ids = self.ids()
        # Max_id is always set to the *smallest* id, minus one, in the set
        return (min(ids) - 1) if ids else None

    @property
    def since_id(self):
        if self._since_id:
            return self._since_id
        ids = self.ids()
        # Since_id is always set to the *greatest* id in the set
        return max(ids) if ids else None

    def ids(self):
        return [item.id for item in self if hasattr(item, 'id')]


class Model(object):

    misspellings = {
        # key: wrong, value: correct
        'cummulative': 'cumulative',
    }

    def __init__(self, api=None):
        self._api = api
        self._fix_spellings = False

    def __getstate__(self, action=None):
        # pickle
        pickle = dict(self.__dict__)
        try:
            for key in [k for k in pickle.keys() if k.startswith('_')]:
                del pickle[key]  # do not pickle private attrs
        except KeyError:
            pass

        if self._fix_spellings:
            for wrong, correct in self.misspellings.items():
                if correct in pickle.keys():
                    pickle[wrong] = pickle.get(correct)
                    del pickle[correct]

        # allow model implementations to mangle state on different api actions
        action_fn = getattr(self, "__getstate_{0}__".format(action), None)
        if action and callable(action_fn):
            pickle = action_fn(pickle)

        return pickle

    def to_state(self, action=None):
        state = self.__getstate__(action)
        return state

    def to_json(self, action=None, indent=None):
        return json.dumps(self.to_state(action), sort_keys=True, cls=SenseTEncoder, indent=indent)  # be explict with key order so unittest work.

    @classmethod
    def parse(cls, api, json_frag):
        instance = cls(api)

        try:
            instance.usermetadata = json_frag['usermetadata']
        except KeyError:
            pass

        return instance

    @classmethod
    def parse_list(cls, api, json_list):
        """
            Parse a list of JSON objects into
            a result set of model instances.
        """
        results = ResultSet()
        for obj in json_list:
            if obj:
                results.append(cls.parse(api, obj))
        return results

    @classmethod
    def fix_parse_misspellings(cls, json_frag):
        for wrong, correct in cls.misspellings.items():
            if wrong in json_frag.keys():
                json_frag[correct] = json_frag.get(wrong)
                del json_frag[wrong]

    def __repr__(self):
        state = ['%s=%s' % (k, repr(v)) for (k, v) in vars(self).items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(state))

    def __eq__(self, other):
        if self.id == other.id:
            return True
        else:
            return False


class JSONModel(Model):
    @classmethod
    def parse(cls, api, json_frag):
        return json_frag


class Platform(Model):
    def __init__(self, api=None):
        super(Platform, self).__init__(api=api)
        self._organisations = list()
        self._groups = list()
        self._streams = list()
        self._deployments = list()

    def __getstate__(self, action=None):
        pickled = super(Platform, self).__getstate__(action)

        pickled["groupids"] = [g.id for g in self.groups]
        pickled["streamids"] = [s.id for s in self.streams]
        pickled["deployments"] = [d.__getstate__(action) for d in self.deployments]
        return pickled

    def __getstate_create__(self, pickled):
        """
        :param pickled: dict of object kay, values
        :return: API weirdly requires a single organisationid on creation/update but returns a list
        """
        if not self.organisations:
            raise SenapsError("Platform creation requires an organisationid.")
        pickled["organisationid"] = self.organisations[0].id
        return pickled

    def __getstate_update__(self, pickled):
        """
        :param pickled: dict of object kay, values
        :return: pointer to self.__getstate_create__
        """
        return self.__getstate_create__(pickled)

    @classmethod
    def parse(cls, api, json_frag):
        platform = super(Platform, cls).parse(api, json_frag)
        setattr(platform, '_json', json_frag)
        for k, v in json_frag.items():
            if k == "_embedded":
                for ek, ev in v.items():
                    if ek == "organisation":
                        setattr(platform, "organisations", Organisation.parse_list(api, ev))
                    elif ek == "groups":
                        setattr(platform, "groups", Group.parse_list(api, ev))
                    elif ek == "platformdeployment":
                        setattr(platform, "deployments", Deployment.parse_list(api, ev))
                    elif ek == "streams":
                        setattr(platform, "streams", Stream.parse_list(api, ev))
            else:
                setattr(platform, k, v)
        return platform

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        elif "_embedded" not in json_list:
            item_list = []
        else:
            item_list = json_list['_embedded']['platforms']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    @property
    def organisations(self):
        return self._organisations

    @organisations.setter
    def organisations(self, value):
        self._organisations = value

    @property
    def groups(self):
        return self._groups

    @groups.setter
    def groups(self, value):
        self._groups = value

    @property
    def streams(self):
        return self._streams

    @streams.setter
    def streams(self, value):
        self._streams = value

    @property
    def deployments(self):
        return self._deployments

    @deployments.setter
    def deployments(self, value):
        self._deployments = value


class Organisation(Model):
    @classmethod
    def parse(cls, api, json_frag):
        organisation = super(Organisation, cls).parse(api, json_frag)
        setattr(organisation, '_json', json_frag)
        for k, v in json_frag.items():
            setattr(organisation, k, v)
        return organisation

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['organisations']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def permissions(self):
        raise NotImplementedError("Not implemented.")


class Vocabulary(Model):
    pass


class StreamMetaData(Model):
    def __init__(self, api=None):
        super(StreamMetaData, self).__init__(api=api)
        self._fix_spellings = True
        self._type = None
        self._interpolation_type = None

        # scalar only attrs
        self._observed_property = None
        self.cumulative = None

        # geo only attrs
        self._unit_of_measure = None

        # simple vector only attrs
        self._length = None
        # regularly binned vector only attrs
        self._start = None
        self._end = None
        self._step = None
        self._amplitude_unit = None
        self._length_unit = None

        # cumulative stream only attrs
        self.accumulationInterval = None
        self.accumulationAnchor = None

        # required for cumulative scalar streams
        self.timezone = None

    def __getstate__(self, action=None):
        pickled = super(StreamMetaData, self).__getstate__(action)

        if self.interpolation_type:
            pickled["interpolationType"] = self.interpolation_type.value

        if self.observed_property:
            pickled["observedProperty"] = self.observed_property

        if self.unit_of_measure:
            pickled["unitOfMeasure"] = self.unit_of_measure

        if self.amplitude_unit:
            pickled["amplitudeUnit"] = self.amplitude_unit

        if self.length_unit:
            pickled["lengthUnit"] = self.length_unit

        # clean up non scalar StreamMetaData keys
        if self._type != StreamMetaDataType.scalar and self._type != StreamMetaDataType.regularly_binned_vector:
            for key in ['observedProperty', 'cumulative']:
                try:
                    del pickled[key]
                except KeyError:
                    pass

        # clean up non geo StreamMetaData keys
        if self._type != StreamMetaDataType.scalar:
            for key in ['unitOfMeasure']:
                try:
                    del pickled[key]
                except KeyError:
                    pass

        # clean up non cumulative stream StreamMetaData keys
        if not self.cumulative:
            for key in ['accumulationInterval', 'accumulationAnchor']:
                try:
                    del pickled[key]
                except KeyError:
                    pass
            if self.cumulative is None:  # different then false in PAI
                del pickled['cummulative']

        if self.timezone is None:
            del pickled["timezone"]

        if action != "create":
            # purge the type, it is never returned on get request
            try:
                del pickled['type']
            except KeyError:
                pass

        return pickled

    def __getstate_create__(self, pickled):
        """
        :param pickled: dict of object kay, values
        :return:
        """
        if not self.type:
            raise SenapsError("Stream creation requires an type.")
        if self.type is not None:
            pickled["type"] = self._type.value
        if self.length is not None:
            pickled["length"] = self._length

        if self.start is not None:
            pickled["start"] = self._start

        if self.end is not None:
            pickled["end"] = self._end

        if self.step is not None:
            pickled["step"] = self._step
        return pickled

    @classmethod
    def parse(cls, api, json_frag):
        stream_meta_data = super(StreamMetaData, cls).parse(api, json_frag)
        cls.fix_parse_misspellings(json_frag)

        setattr(stream_meta_data, '_json', json_frag)
        for k, v in json_frag.items():
            if k == "type":
                setattr(stream_meta_data, "type", StreamMetaDataType(v))
            elif k == "_embedded":
                for ek, ev in v.items():
                    if ek == "interpolationType":
                        ev = ev[0].get('_links', {}).get('self', {}).get('href', )
                        setattr(stream_meta_data, "interpolation_type", InterpolationType(ev))
                    elif ek == "observedProperty":
                        ev = ev[0].get('_links', {}).get('self', {}).get('href', )
                        # Remove local vocab checks for now
                        setattr(stream_meta_data, "observed_property", ev)
                    elif ek == "unitOfMeasure":
                        ev = ev[0].get('_links', {}).get('self', {}).get('href', )
                        # Remove local vocab checks for now
                        setattr(stream_meta_data, "unit_of_measure", ev)
                    elif ek == "amplitudeUnit":
                        ev = ev[0].get('_links', {}).get('self', {}).get('href', )
                        # Remove local vocab checks for now
                        setattr(stream_meta_data, "amplitude_unit", ev)
                    elif ek == "lengthUnit":
                        ev = ev[0].get('_links', {}).get('self', {}).get('href', )
                        # Remove local vocab checks for now
                        setattr(stream_meta_data, "length_unit", ev)
                    else:
                        setattr(stream_meta_data, ek, ev)
                        print("parse: %s, %s" % (ek, ev))
            else:
                setattr(stream_meta_data, k, v)
        return stream_meta_data

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def interpolation_type(self):
        return self._interpolation_type

    @interpolation_type.setter
    def interpolation_type(self, value):
        self._interpolation_type = value

    @property
    def observed_property(self):
        return self._observed_property

    @observed_property.setter
    def observed_property(self, value):
        self._observed_property = value

    @property
    def unit_of_measure(self):
        return self._unit_of_measure

    @unit_of_measure.setter
    def unit_of_measure(self, value):
        self._unit_of_measure = value

    # vector properties
    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = value

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        self._end = value

    @property
    def step(self):
        return self._step

    @step.setter
    def step(self, value):
        self._step = value

    @property
    def amplitude_unit(self):
        return self._amplitude_unit

    @amplitude_unit.setter
    def amplitude_unit(self, value):
        self._amplitude_unit = value

    @property
    def length_unit(self):
        return self._length_unit

    @length_unit.setter
    def length_unit(self, value):
        self._length_unit = value

class Stream(Model):
    def __init__(self, api=None):
        super(Stream, self).__init__(api=api)
        self._result_type = None
        self._organisations = list()
        self._groups = list()
        self._metadata = None
        self._location = None

    def __getstate__(self, action=None):
        pickled = super(Stream, self).__getstate__(action)

        pickled["resulttype"] = self._result_type.value if self._result_type is not None else None
        pickled["organisationid"] = self.organisations[0].id

        if self.groups:
            pickled["groupids"] = [g.id for g in self.groups]

        try:
            if self.location:
                pickled["locationid"] = self.location.id
        except AttributeError:
            # excetion will be thrown if location is not specified and current object does not have a location
            pass

        if self.metadata:
            pickled["streamMetadata"] = self.metadata.__getstate__(action)

        return pickled

    @classmethod
    def parse(cls, api, json_frag):
        stream = super(Stream, cls).parse(api, json_frag)
        setattr(stream, '_json', json_frag)
        for k, v in json_frag.items():
            if k == "resulttype":
                setattr(stream, "result_type", StreamResultType(v))
            elif k == "_embedded":
                for ek, ev in v.items():
                    if ek == "organisation":
                        setattr(stream, "organisations", Organisation.parse_list(api, ev))
                    elif ek == "groups":
                        setattr(stream, "groups", Group.parse_list(api, ev))
                    elif ek == "location":
                        setattr(stream, "location", Location.parse(api, ev[0]))
                    elif ek == "metadata":
                        # metadata is also a list ?????
                        setattr(stream, "metadata", StreamMetaData.parse(api, ev[0]))
            else:
                setattr(stream, k, v)
        return stream

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['_embedded']['streams']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    @property
    def result_type(self):
        return self._result_type

    @result_type.setter
    def result_type(self, value):
        self._result_type = value

    @property
    def organisations(self):
        return self._organisations

    @organisations.setter
    def organisations(self, value):
        self._organisations = value

    @property
    def groups(self):
        return self._groups

    @groups.setter
    def groups(self, value):
        self._groups = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value


class Group(Model):
    @classmethod
    def parse(cls, api, json_frag):
        group = super(Group, cls).parse(api, json_frag)
        setattr(group, '_json', json_frag)
        for k, v in json_frag.items():
            setattr(group, k, v)
        return group

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list.get('_embedded', {}).get('groups', [])

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results


# TODO - not all attributes are implemented
class Location(Model):

    def __init__(self, api=None):
        super(Location, self).__init__(api=api)
        self._organisations = list()
        self._groups = list()

    @classmethod
    def parse(cls, api, json_frag):
        location = super(Location, cls).parse(api, json_frag)

        setattr(location, '_json', json_frag)
        for k, v in json_frag.items():
            setattr(location, k, v)

        return location

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['_embedded']['locations']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def __getstate__(self, action=None):
        pickled = super(Location, self).__getstate__(action)
        pickled["groupids"] = [g.id for g in self.groups]
        pickled["organisationid"] = self.organisations[0].id

        return pickled

    @property
    def organisations(self):
        return self._organisations

    @organisations.setter
    def organisations(self, value):
        self._organisations = value

    @property
    def groups(self):
        return self._groups

    @groups.setter
    def groups(self, value):
        self._groups = value

class Procedure(Model):
    pass


class Observation(Model):
    def __init__(self, api=None):
        super(Observation, self).__init__(api=api)
        self._results = list()
        self._stream = None

    def __getstate__(self, action=None):
        pickled = super(Observation, self).__getstate__(action)

        pickled["results"] = [r.to_state(action) for r in self.results] if self.results else []
        if self.stream:
            pickled["streamid"] = self.stream.to_state(action).get("id")
        return pickled

    @classmethod
    def parse(cls, api, json_frag):
        observation = super(Observation, cls).parse(api, json_frag)
        setattr(observation, '_json', json_frag)
        for k, v in json_frag.items():
            if k == "results":
                setattr(observation, "results", UnivariateResult.parse_list(api, v))
            if k == "stream":
                setattr(observation, "stream", Stream.parse(api, v))
            else:
                setattr(observation, k, v)
        return observation

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['observations']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results
    
    @classmethod
    def from_dataframe(cls, dataframe):
        result = {}
         
        for timestamp, series in dataframe.iterrows():
            timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            for series_id, value in series.iteritems():
                observation = UnivariateResult(t=timestamp, v=value)
                result.setdefault(series_id, Observation()).results.append(observation)
        return result

    @property
    def results(self):
        return self._results

    @results.setter
    def results(self, value):
        self._results = value

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value):
        self._stream = value

class Aggregation(Model):
    pass


class UnivariateResult(JSONModel):
    def __init__(self, api=None, t=None, v=None):
        super(UnivariateResult, self).__init__(api=api)
        self.t = t
        self.v = v

    def __getstate__(self, action=None):
        pickled = super(UnivariateResult, self).__getstate__(action)

        if isinstance(pickled.get('t', None), datetime.datetime):
            pickled['t'] = pickled.get('t').strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return pickled


class Deployment(Model):
    @classmethod
    def parse(cls, api, json_frag):
        deployment = super(Deployment, cls).parse(api, json_frag)
        setattr(deployment, '_json', json_frag)

        for k, v in json_frag.items():
            if k == "_embedded":
                for ek, ev in v.items():
                    if ek == "location":
                        setattr(deployment, "_location", Location.parse(api, ev[0]))
            else:
                setattr(deployment, k, v)

        return deployment

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['deployments']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def __getstate__(self, action=None):
        pickled = super(Deployment, self).__getstate__(action)

        if self.location:
           pickled["locationid"] = self.location.id

        return pickled

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    def permissions(self):
        raise NotImplementedError("Not implemented.")


class Role(Model):

    @classmethod
    def parse(cls, api, json_frag):
        role = super(Role, cls).parse(api, json_frag)
        setattr(role, '_json', json_frag)
        for k, v in json_frag.items():
            setattr(role, k, v)

        # look for org + groupid in _embedded data.
        # nb: these aren't always present, need to be careful with check.
        if '_embedded' not in json_frag:
            return role

        # admin, org, and group type roles, each comes with different embedded data.
        if 'group' in json_frag['_embedded']:
            setattr(role, 'groupid', json_frag['_embedded']['group'][0]['id'])
        if 'organisation' in json_frag['_embedded']:
            setattr(role, 'organisationid', json_frag['_embedded']['organisation'][0]['id'])

        return role

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['_embedded']['roles']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def permissions(self):
        raise NotImplementedError("Not implemented.")


class User(Model):

    @classmethod
    def parse(cls, api, json_frag):
        user = super(User, cls).parse(api, json_frag)
        attrs = [
            'id',
            'hidden',
            '_links',
            '_embedded',
        ]
        setattr(user, '_json', json_frag)
        for k, v in json_frag.items():
            if k in attrs:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['_embedded']['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    @property
    def roles(self):
        if hasattr(self, '_embedded') and 'roles' in self._embedded.keys():
            return Role.parse_list(self._api, self._embedded.get('roles'))
        return None

    def groups(self):
        pass

class Permitted(Model):

    @classmethod
    def parse(cls, api, json_frag):
        permitted = super(Permitted, cls).parse(api, json_frag)
        attrs = [
            '_links',
            '_embedded',
        ]
        setattr(permitted, '_json', json_frag)
        setattr(permitted, 'permitted', json_frag['permitted'])
        for k, v in json_frag.items():
            if k in attrs:
                setattr(permitted, k, v)

        return permitted

    @property
    def user(self):
        if hasattr(self, '_embedded') and 'user' in self._embedded.keys():
            return User.parse(self._api, self._embedded.get('user')[0])
        return None


class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """
    user = User
    organisation = Organisation
    group = Group
    role = Role
    vocabulary = Vocabulary
    stream = Stream
    platform = Platform
    location = Location
    procedure = Procedure
    observation = Observation
    aggregation = Aggregation
    permitted = Permitted

    json = JSONModel

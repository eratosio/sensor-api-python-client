Senaps Sensor Data Python Client
==============================

This project is a python client implementation for the [Senaps Sensor API v2](https://senaps.eratos.com/api-docs/).

Project home page: https://github.com/eratosio/sensor-api-python-client

Installation
------------

Install from the default branch:

    $ pip install -e git+https://github.com/eratosio/sensor-api-python-client.git#egg=eratos-sensor

Or install from a tag:

    $ pip install -e git+https://github.com/eratosio/sensor-api-python-client.git@v2.17.0#egg=eratos-sensor

Documentation
------------

TODO

Roadmap
------------

* Define unimplemented models
* Define unimplemented API endpoints

Development
------------

Clone the project from github:

    $ git clone https://github.com/eratosio/sensor-api-python-client.git
    $ cd sensor-api-python-client

Create a python virtual environment, then install the requirements as below:

    $ (venv) pip install -r requirements.txt && pip install -r test_requirements.txt

Testing
------------

Run the test suite with:

    $ (venv) nosetests -v tests.test_auth tests.test_api tests.test_internal_auth tests.test_parsers

Or, use `tox` to run the setup.py package build and test suite for all python versions (ensure your environment variables for any API calls that hit the web are correct, see `tox.ini` passenv configuration):

    $ (venv) tox

#### Acknowledgements

This project has been heavily derived from the Tweepy python twitter client project: https://github.com/tweepy/tweepy/ 

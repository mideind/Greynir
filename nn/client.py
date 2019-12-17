#!/usr/bin/env python3
"""
    Reynir: Natural language processing for Icelandic

    Neural Network Query Client

    Copyright (C) 2018 Miðeind ehf.

       This program is free software: you can redistribute it and/or modify
       it under the terms of the GNU General Public License as published by
       the Free Software Foundation, either version 3 of the License, or
       (at your option) any later version.
       This program is distributed in the hope that it will be useful,
       but WITHOUT ANY WARRANTY; without even the implied warranty of
       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
       GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses/.

    This module implements a client that connects to a middleware
    neural network server (see nnserver/nnserver.py), which in turn
    connects to a TensorFlow model server.

"""

import json

from flask import abort
import requests

from nn.utils import split_text
from settings import Settings


class ApiClient:

    port = None
    host = None
    action = None
    https = True
    url = None

    data = None

    required_fields = []
    default_field_values = []
    headers = {"content-type": "application/json; charset=UTF-8"}

    def __init__(self, port=None, host=None, https=None, action=None):
        if port is not None:
            self.port = port
        if host is not None:
            self.host = host
        if https is not None:
            self.https = https
        if action is not None:
            self.action = action

        self._set_url()

    def _set_url(self):
        https_char = ''
        if self.https:
            https_char = 's'

        self.url = "http{https_char}://{host}:{port}/{action}".format(
            https_char=https_char,
            host=self.host,
            port=self.port,
            action=self.action
        )

    def validate(self, request):

        data = json.loads(request.data)
        required_diff = set(self.required_fields).difference(data.keys())
        if required_diff:
            return (False,  "{} are required fields.".format(", ".join(required_diff)))

        for field in self.default_field_values:
            if field not in data:
                data[field] = self.default_field_values[field]

        return (True, data)

    def parse_for_remote(self, data):
        return {
            "pgs": data['contents']
        }

    def get(self, data):
        response = requests.get(self.url, json.dumps(data), headers=self.headers)
        return json.loads(response.text)

    def post(self, data):
        response = requests.post(self.url, json.dumps(data), headers=self.headers)
        return response.text

    def dispatch(self, request):
        valid, data = self.validate(request)
        if not valid:
            return abort(400, data)

        self.data = data

        parsed_data = self.parse_for_remote(data)

        if request.method == 'POST':
            return self.post(parsed_data)

        if request.method == 'GET':
            return self.get(parsed_data)

        return abort(400, 'Bad method {}'.format(request.method))


class TranslationApiClient(ApiClient):
    required_fields = (
        "contents",
    )

    target = "en"
    source = "is"

    default_field_values = {
        "targetLanguageCode": "en",
        "sourceLanguageCode": "is"
    }

    port = Settings.NN_TRANSLATE_PORT
    host = Settings.NN_TRANSLATE_HOST
    action = "translate.api"

    https = False

    def post(self, data):
        response = json.loads(super(TranslationApiClient, self).post(data))
        return json.dumps(
            {
                "translations": [
                    {
                        "translatedText": val["outputs"],
                        "scores": val["scores"],  # Not part of the Google API
                        "model": "{}-{}".format(
                            self.data['sourceLanguageCode'],
                            self.data['targetLanguageCode'],
                        )
                    } for val in response["predictions"]]
            }
        )

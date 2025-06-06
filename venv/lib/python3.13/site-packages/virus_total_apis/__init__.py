#!/usr/bin/env python
# -*- coding: utf-8 -*-

__title__ = 'virustotal-api'
__version__ = '1.1.11'
__author__ = 'Josh Maine'
__license__ = 'MIT'
__copyright__ = 'Copyright (C) 2014-2017 Josh "blacktop" Maine'

try:
    import requests
except ImportError:
    pass

from .api import ApiError, IntelApi, PrivateApi, PublicApi

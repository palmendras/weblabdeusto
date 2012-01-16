#!/usr/bin/env python
#-*-*- encoding: utf-8 -*-*-
#
# Copyright (C) 2005-2009 University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals, 
# listed below:
#
# Author: Pablo Orduña <pablo@ordunya.com>
#

from voodoo.representable import Representable

class Resource(object):
    __metaclass__ = Representable

    def __init__(self, resource_type, resource_instance):
        self.resource_type     = resource_type
        self.resource_instance = resource_instance


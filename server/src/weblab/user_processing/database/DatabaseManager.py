#!/usr/bin/python
# -*- coding: utf-8 -*-
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
#         Jaime Irurzun <jaime.irurzun@gmail.com>
# 

import weblab.user_processing.database.DatabaseGateway as DbGateway

class UserProcessingDatabaseManager(object):
    
    def __init__(self, cfg_manager):
        super(UserProcessingDatabaseManager, self).__init__()
        self._gateway = DbGateway.create_gateway(cfg_manager)

    def retrieve_user_information(self, session_id):
        return self._gateway.get_user_by_name( session_id.username )
   
    def get_available_experiments(self, session_id):
        return self._gateway.list_experiments( session_id.username )
    
    def store_experiment_usage(self, session_id, experiment_usage):
        return self._gateway.store_experiment_usage( session_id.username, experiment_usage )
    
    def get_groups(self, session_id):
        return self._gateway.get_groups( session_id.username )
    
    def get_users(self, session_id):
        """
        Retrieves the users through the database gateway
        """
        return self._gateway.get_users( )
    
    def get_experiments(self, session_id):
        return self._gateway.get_experiments( session_id.username )
    
    def get_experiment_uses(self, session_id, from_date, to_date, group_id, experiment_id):
        return self._gateway.get_experiment_uses( session_id.username, from_date, to_date, group_id, experiment_id )
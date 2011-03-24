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

try:
    import json as json_mod
    json = json_mod
except ImportError:
    import simplejson as json_module
    json = json_module

from voodoo.threaded import threaded
import voodoo.log as log

import voodoo.ResourceManager as ResourceManager
import voodoo.gen.coordinator.CoordAddress as CoordAddress
import voodoo.sessions.SessionId as SessionId

import weblab.data.ServerType as ServerType

_resource_manager = ResourceManager.CancelAndJoinResourceManager("Coordinator")

class ReservationConfirmer(object):
    def __init__(self, coordinator, locator):
        self.coordinator                        = coordinator
        self.locator                            = locator
        self._enqueuing_timeout                 = 0
        self._initialize_and_dispose_experiment = True

    def _get_enqueuing_timeout(self):
        return self._enqueuing_timeout

    def _set_enqueuing_timeout(self, value):
        self._enqueuing_timeout = value

    enqueuing_timeout = property(_get_enqueuing_timeout, _set_enqueuing_timeout)

    def enqueue_confirmation(self, lab_coordaddress_str, reservation_id, experiment_instance_id, client_initial_data, server_initial_data):
        # We can stablish a politic such as using 
        # thread pools or a queue of threads or something
        # like that... here
        lab_coordaddress = CoordAddress.CoordAddress.translate_address(lab_coordaddress_str)
        self._confirm_handler = self._confirm_experiment(lab_coordaddress, reservation_id, experiment_instance_id, client_initial_data, server_initial_data)
        self._confirm_handler.join(self._enqueuing_timeout)

    @threaded(_resource_manager)
    def _confirm_experiment(self, lab_coordaddress, reservation_id, experiment_instance_id, client_initial_data, server_initial_data):
        try:
            labserver = self.locator.get_server_from_coordaddr(lab_coordaddress, ServerType.Laboratory)
            lab_session_id, server_initialization_response = labserver.reserve_experiment(experiment_instance_id, client_initial_data, server_initial_data)
        except Exception, e:
            self.coordinator.mark_experiment_as_broken(experiment_instance_id, [str(e)])

            log.log( ReservationConfirmer, log.LogLevel.Error, "Exception confirming experiment: %s" % e )
            log.log_exc( ReservationConfirmer, log.LogLevel.Warning )
        else:
            if server_initialization_response is None or server_initialization_response == 'ok' or server_initialization_response == '':
                still_initializing = False
                batch = False
                initial_configuration = "{}"
            else:
                try:
                    response = json.loads(server_initialization_response)
                    still_initializing    = response.get('keep_initializing', False)
                    batch                 = response.get('batch', False)
                    initial_configuration = response.get('initial_configuration', "{}")
                except Exception, e:
                    self.coordinator.mark_experiment_as_broken(experiment_instance_id, [str(e)])

                    log.log( ReservationConfirmer, log.LogLevel.Error, "Could not parse experiment server response: %s; %s" % (e, server_initialization_response) )
                    log.log_exc( ReservationConfirmer, log.LogLevel.Warning )
                    return
                   
            self.coordinator.confirm_experiment(reservation_id, lab_session_id)


    def enqueue_free_experiment(self, lab_coordaddress_str, lab_session_id):
        # We can stablish a politic such as using 
        # thread pools or a queue of threads or something
        # like that... here
        lab_coordaddress = CoordAddress.CoordAddress.translate_address(lab_coordaddress_str)
        self._free_handler = self._free_experiment(lab_coordaddress, lab_session_id)
        self._free_handler.join(self._enqueuing_timeout)


    @threaded(_resource_manager)
    def _free_experiment(self, lab_coordaddress, lab_session_id):
        try:
            labserver = self.locator.get_server_from_coordaddr(lab_coordaddress, ServerType.Laboratory)
            labserver.free_experiment(SessionId.SessionId(lab_session_id))
        except Exception, e:
            log.log( ReservationConfirmer, log.LogLevel.Error, "Exception freeing experiment: %s" % e )
            log.log_exc( ReservationConfirmer, log.LogLevel.Warning )

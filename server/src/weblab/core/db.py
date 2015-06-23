#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005 onwards University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals,
# listed below:
#
# Author: Jaime Irurzun <jaime.irurzun@gmail.com>
#         Pablo Orduña <pablo@ordunya.com>
#

import os
import numbers
import datetime
import threading
import traceback
from functools import wraps
from collections import OrderedDict, namedtuple

import sqlalchemy
import sqlalchemy.sql as sql
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

import voodoo.log as log
from voodoo.log import logged
from voodoo.typechecker import typecheck

from weblab.db import db
import weblab.db.model as model

import weblab.configuration_doc as configuration_doc
from weblab.data import ValidDatabaseSessionId
from weblab.data.command import Command
import weblab.data.dto.experiments as ExperimentAllowed
from weblab.data.experiments import ExperimentUsage, CommandSent, FileSent

import weblab.core.exc as DbErrors
import weblab.permissions as permissions

DEFAULT_VALUE = object()

_current = threading.local()
class UsesQueryParams( namedtuple('UsesQueryParams', ['login', 'experiment_name', 'category_name', 'group_names', 'start_date', 'end_date'])):
    PRIVATE_FIELDS = ('group_names',)
    def pubdict(self):
        result = {}
        for field in UsesQueryParams._fields:
            if field not in self.PRIVATE_FIELDS and getattr(self, field) is not None:
                result[field] = getattr(self, field)
        return result

# Support None as default params
UsesQueryParams.__new__.__defaults__ = (None,) * len(UsesQueryParams._fields)

def with_session(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _current.session = self.Session()
        try:
            return func(self, *args, **kwargs)
        except sqlalchemy.exc.SQLAlchemyError:
            _current.session.rollback()
            raise
        finally:
            _current.session.close()

    return wrapper

class DatabaseGateway(object):

    forbidden_access = 'forbidden_access'

    def __init__(self, cfg_manager):
        super(DatabaseGateway, self).__init__()
        self.cfg_manager = cfg_manager
        self.Session, self.engine = db.initialize(cfg_manager)

    @typecheck(basestring)
    @logged()
    def get_user_by_name(self, user_login):
        session = self.Session()
        try:
            return self._get_user(session, user_login).to_dto()
        finally:
            session.close()

    @logged()
    def list_clients(self):
        """Lists the ExperimentClients """
        session = self.Session()
        try:
            clients = {}
            for experiment in session.query(model.DbExperiment).all():
                exp = experiment.to_business()
                clients[exp.name, exp.category.name] = exp.client
            return clients
        finally:
            session.close()

    @logged()
    def get_client_id(self, experiment_name, category_name):
        """Lists the ExperimentClients """
        session = self.Session()
        try:
            category = session.query(model.DbExperimentCategory).filter_by(name = category_name).first()
            if category is None:
                return None
            experiment = session.query(model.DbExperiment).filter_by(name = experiment_name, category = category).first()
            if experiment is None:
                return None
            return experiment.client
        finally:
            session.close()

    # @typecheck(basestring, (basestring, None), (basestring, None))
    @logged()
    def list_experiments(self, user_login, exp_name = None, cat_name = None):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            user_permissions = self._gather_permissions(session, user, 'experiment_allowed')

            grouped_experiments = {}
            for permission in user_permissions:
                p_permanent_id                 = self._get_parameter_from_permission(session, permission, 'experiment_permanent_id')
                p_category_id                  = self._get_parameter_from_permission(session, permission, 'experiment_category_id')
                p_time_allowed                 = self._get_float_parameter_from_permission(session, permission, 'time_allowed')
                p_priority                     = self._get_int_parameter_from_permission(session, permission, 'priority', ExperimentAllowed.DEFAULT_PRIORITY)
                p_initialization_in_accounting = self._get_bool_parameter_from_permission(session, permission, 'initialization_in_accounting', ExperimentAllowed.DEFAULT_INITIALIZATION_IN_ACCOUNTING)
                
                # If a filter is passed, ignore those permissions on other experiments
                if cat_name is not None and exp_name is not None:
                    if p_category_id != cat_name or p_permanent_id != exp_name:
                        continue
                experiments = [ exp for exp in session.query(model.DbExperiment).filter_by(name=p_permanent_id).all() if exp.category.name == p_category_id ]
                if len(experiments) == 0:
                    continue

                experiment = experiments[0]

                if isinstance(permission, model.DbUserPermission):
                    permission_scope = 'user'
                elif isinstance(permission, model.DbGroupPermission):
                    permission_scope = 'group'
                elif isinstance(permission, model.DbRolePermission):
                    permission_scope = 'role'
                else:
                    permission_scope = 'unknown'
                experiment_allowed = ExperimentAllowed.ExperimentAllowed(experiment.to_business(), p_time_allowed, p_priority, p_initialization_in_accounting, permission.permanent_id, permission.id, permission_scope)

                experiment_unique_id = p_permanent_id+"@"+p_category_id
                if experiment_unique_id in grouped_experiments:
                    grouped_experiments[experiment_unique_id].append(experiment_allowed)
                else:
                    grouped_experiments[experiment_unique_id] = [experiment_allowed]

            # If any experiment is duplicated, only the less restrictive one is given
            experiments = []
            for experiment_unique_id in grouped_experiments:
                less_restrictive_experiment_allowed = grouped_experiments[experiment_unique_id][0]
                for experiment_allowed in grouped_experiments[experiment_unique_id]:
                    if experiment_allowed.time_allowed > less_restrictive_experiment_allowed.time_allowed:
                        less_restrictive_experiment_allowed = experiment_allowed
                experiments.append(less_restrictive_experiment_allowed)

            experiments.sort(lambda x,y: cmp(x.experiment.category.name, y.experiment.category.name))
            return tuple(experiments)
        finally:
            session.close()

    @typecheck(basestring)
    @logged()
    def is_access_forward(self, user_login):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            user_permissions = self._gather_permissions(session, user, 'access_forward')
            return len(user_permissions) > 0
        finally:
            session.close()

    @typecheck(basestring)
    @logged()
    def is_admin(self, user_login):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            user_permissions = self._gather_permissions(session, user, 'admin_panel_access')
            return len(user_permissions) > 0
        finally:
            session.close()

    @typecheck(basestring)
    @logged()
    def is_instructor(self, user_login):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            admin_permissions = self._gather_permissions(session, user, 'admin_panel_access')
            instructor_permissions = self._gather_permissions(session, user, 'instructor_of_group')
            return user.role.name == 'instructor' or len(admin_permissions) > 0 or len(instructor_permissions) > 0
        finally:
            session.close()


    @typecheck(basestring, ExperimentUsage)
    @logged()
    def store_experiment_usage(self, user_login, experiment_usage):
        session = self.Session()
        try:
            use = model.DbUserUsedExperiment(
                        self._get_user(session, user_login),
                        self._get_experiment(session, experiment_usage.experiment_id.exp_name, experiment_usage.experiment_id.cat_name),
                        experiment_usage.start_date,
                        experiment_usage.from_ip,
                        experiment_usage.coord_address.address,
                        experiment_usage.reservation_id,
                        experiment_usage.end_date,
                )
            session.add(use)
            # TODO: The c.response of an standard command is an object with
            # a commandstring, whereas the response to an async command is
            # a simple string to identify the request. The way in which the logger
            # currently handles these cases is somewhat shady.
            for c in experiment_usage.commands:
                # If we have a response, the c.response will be an object and not
                # a string. Generally, we will, unless the command was asynchronous
                # and it didn't finish executing.
                if type(c.response) != type(""):
                    session.add(model.DbUserCommand(
                                    use,
                                    c.command.commandstring,
                                    c.timestamp_before,
                                    c.response.commandstring,
                                    c.timestamp_after
                                ))
                else:
                    # In this other case, the response is a string, which means
                    # that we have not updated it with the real response. Probably,
                    # it was an asynchronous command which did not finish executing
                    # by the time the experiment ended.
                    session.add(model.DbUserCommand(
                                    use,
                                    c.command.commandstring,
                                    c.timestamp_before,
                                    "[RESPONSE NOT AVAILABLE]",
                                    c.timestamp_after
                                ))
            for f in experiment_usage.sent_files:
                if f.is_loaded():
                    saved = f.save(self.cfg_manager, experiment_usage.reservation_id)
                else:
                    saved = f
                session.add(model.DbUserFile(
                                use,
                                saved.file_path,
                                saved.file_hash,
                                saved.timestamp_before,
                                saved.file_info,
                                saved.response.commandstring,
                                saved.timestamp_after
                            ))
            
            permission_scope = experiment_usage.request_info.pop('permission_scope')
            permission_id = experiment_usage.request_info.pop('permission_id')
            if permission_scope == 'group':
                use.group_permission_id = permission_id
            elif permission_scope == 'user':
                use.user_permission_id = permission_id
            elif permission_scope == 'role':
                use.role_permission_id = permission_id

            for reservation_info_key in experiment_usage.request_info:
                db_key = session.query(model.DbUserUsedExperimentProperty).filter_by(name = reservation_info_key).first()
                if db_key is None:
                    db_key = model.DbUserUsedExperimentProperty(reservation_info_key)
                    session.add(db_key)

                value = experiment_usage.request_info[reservation_info_key]
                session.add(model.DbUserUsedExperimentPropertyValue( unicode(value), db_key, use ))

            session.commit()
        finally:
            session.close()

    @typecheck(basestring, float, CommandSent)
    @logged()
    def finish_experiment_usage(self, reservation_id, end_date, last_command ):
        session = self.Session()
        try:
            user_used_experiment = session.query(model.DbUserUsedExperiment).filter_by(reservation_id = reservation_id).first()
            if user_used_experiment is None:
                return False

            user_used_experiment.set_end_date(end_date)
            session.add(user_used_experiment)
            session.add(model.DbUserCommand(
                            user_used_experiment,
                            last_command.command.commandstring,
                            last_command.timestamp_before,
                            last_command.response.commandstring,
                            last_command.timestamp_after
                        ))
            session.commit()
            return True
        finally:
            session.close()

    @logged()
    def store_commands(self, complete_commands, command_requests, command_responses, complete_files, file_requests, file_responses):
        """ Stores all the commands in a single transaction; retrieving the ids of the file and command requests """
        request_mappings = {
            # entry_id : command_id
        }
        session = self.Session()
        try:
            db_commands_and_files = []

            for reservation_id, entry_id, command in complete_commands:
                db_command = self._append_command(session, reservation_id, command)
                if db_command == False:
                    request_mappings[entry_id] = False

            for reservation_id, entry_id, command in complete_files:
                db_file = self._append_file(session, reservation_id, command)
                if db_file == False:
                    request_mappings[entry_id] = False

            for entry_id in command_requests:
                reservation_id, command = command_requests[entry_id]
                db_command = self._append_command(session, reservation_id, command)
                if db_command == False:
                    request_mappings[entry_id] = False
                else:
                    db_commands_and_files.append((entry_id, db_command))

            for entry_id in file_requests:
                reservation_id, file = file_requests[entry_id]
                db_file = self._append_file(session, reservation_id, file)
                if db_file == False:
                    request_mappings[entry_id] = False
                else:
                    db_commands_and_files.append((entry_id, db_file))

            for entry_id, command_id, response, timestamp in command_responses:
                if not self._update_command(session, command_id, response, timestamp):
                    request_mappings[entry_id] = False

            for entry_id, file_id, response, timestamp in file_responses:
                if not self._update_file(session, file_id, response, timestamp):
                    request_mappings[entry_id] = False

            session.commit()
            for entry_id, db_command in db_commands_and_files:
                request_mappings[entry_id] = db_command.id

        finally:
            session.close()
       
        return request_mappings

    @typecheck(basestring, CommandSent)
    @logged()
    def append_command(self, reservation_id, command ):
        session = self.Session()
        try:
            db_command = self._append_command(session, reservation_id, command)
            session.commit()
            return db_command.id
        finally:
            session.close()

    def _append_command(self, session, reservation_id, command):
        user_used_experiment = session.query(model.DbUserUsedExperiment).filter_by(reservation_id = reservation_id).first()
        if user_used_experiment is None:
            return False
        db_command = model.DbUserCommand(
                        user_used_experiment,
                        command.command.commandstring,
                        command.timestamp_before,
                        command.response.commandstring if command.response is not None else None,
                        command.timestamp_after
                    )
        session.add(db_command)
        return db_command

    @typecheck(numbers.Integral, Command, float)
    @logged()
    def update_command(self, command_id, response, end_timestamp ):
        session = self.Session()
        try:
            if self._update_command(session, command_id, response, end_timestamp):
                session.commit()
                return True
            return False
        finally:
            session.close()

    def _update_command(self, session, command_id, response, end_timestamp):
        db_command = session.query(model.DbUserCommand).filter_by(id = command_id).first()
        if db_command is None:
            return False

        db_command.response = response.commandstring if response is not None else None
        db_command.set_timestamp_after(end_timestamp)
        session.add(db_command)
        return True


    @typecheck(basestring, FileSent)
    @logged()
    def append_file(self, reservation_id, file_sent):
        session = self.Session()
        try:
            db_file_sent = self._append_file(session, reservation_id, file_sent)
            session.commit()
            return db_file_sent.id
        finally:
            session.close()

    def _append_file(self, session, reservation_id, file_sent):
        user_used_experiment = session.query(model.DbUserUsedExperiment).filter_by(reservation_id = reservation_id).first()
        if user_used_experiment is None:
            return False
        db_file_sent = model.DbUserFile(
                        user_used_experiment,
                        file_sent.file_path,
                        file_sent.file_hash,
                        file_sent.timestamp_before,
                        file_sent.file_info,
                        file_sent.response.commandstring if file_sent.response is not None else None,
                        file_sent.timestamp_after
                    )
        session.add(db_file_sent)
        return db_file_sent

    @typecheck(numbers.Integral, Command, float)
    @logged()
    def update_file(self, file_id, response, end_timestamp ):
        session = self.Session()
        try:
            if self._update_file(session, file_id, response, end_timestamp):
                session.commit()
                return True
            return False
        finally:
            session.close()

    def _update_file(self, session, file_id, response, end_timestamp):
        db_file_sent = session.query(model.DbUserFile).filter_by(id = file_id).first()
        if db_file_sent is None:
            return False

        db_file_sent.response = response.commandstring if response is not None else None
        db_file_sent.set_timestamp_after(end_timestamp)
        session.add(db_file_sent)
        return True

    @logged()
    def list_usages_per_user(self, user_login, first=0, limit=20):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            uses = session.query(model.DbUserUsedExperiment).filter_by(user=user).offset(first).limit(limit).all()
            return [ use.to_business_light() for use in uses ]
        finally:
            session.close()

    @logged()
    def retrieve_usage(self, usage_id):
        session = self.Session()
        try:
            use = session.query(model.DbUserUsedExperiment).filter_by(id=usage_id).one()
            return use.to_business()
        finally:
            session.close()

    @logged()
    def get_experiment_uses_by_id(self, user_login, reservation_ids):
        """ Retrieve the full information of these reservation_ids, if the user has permissions to do so. By default
         a user can only access to those reservations that he made in the past."""

        results = []
        session = self.Session()
        try:
            user = session.query(model.DbUser).filter_by(login = user_login).first()
            if user is None:
                return [self.forbidden_access] * len(reservation_ids)

            for reservation_id in reservation_ids:
                experiment_use = session.query(model.DbUserUsedExperiment).filter_by(reservation_id = reservation_id.id).first()
                if experiment_use is None:
                    results.append(None)
                else:
                    if experiment_use.user == user:
                        results.append(experiment_use.to_business())
                    else:
                        results.append(self.forbidden_access)
        finally:
            session.close()

        return results

    @logged()
    def get_user_permissions(self, user_login):
        session = self.Session()
        try:
            user = self._get_user(session, user_login)
            user_permissions = []
            for pt in permissions.permission_types:
                user_permissions.extend(self._gather_permissions(session, user, pt))
            dto_permissions = [ permission.to_dto() for permission in user_permissions ]
            return tuple(dto_permissions)
        finally:
            session.close()

    def _get_user(self, session, user_login):
        try:
            return session.query(model.DbUser).filter_by(login=user_login).one()
        except NoResultFound:
            raise DbErrors.DbProvidedUserNotFoundError("Unable to find a User with the provided login: '%s'" % user_login)

    def _get_experiment(self, session, exp_name, cat_name):
        try:
            return session.query(model.DbExperiment) \
                        .filter(model.DbExperimentCategory.name == cat_name) \
                        .filter_by(name=exp_name).one()
        except NoResultFound:
            raise DbErrors.DbProvidedExperimentNotFoundError("Unable to find an Experiment with the provided unique id: '%s@%s'" % (exp_name, cat_name))

    def _gather_groups_permissions(self, session, group, permission_type_name, permissions, remaining_list):
        if group.id in remaining_list:
            return

        remaining_list.append(group.id)
        self._add_or_replace_permissions(permissions, self._get_permissions(session, group, permission_type_name))
        
        if group.parent is not None:
            self._gather_groups_permissions(session, group.parent, permission_type_name, permissions, remaining_list)
        
        

    def _gather_permissions(self, session, user, permission_type_name):
        permissions = []
        self._add_or_replace_permissions(permissions, self._get_permissions(session, user.role, permission_type_name))

        remaining_list = []
        for group in user.groups:
            self._gather_groups_permissions(session, group, permission_type_name, permissions, remaining_list)

        self._add_or_replace_permissions(permissions, self._get_permissions(session, user, permission_type_name))
        return permissions

    def _add_or_replace_permissions(self, permissions, permissions_to_add):
        permissions.extend(permissions_to_add)

    def _get_permissions(self, session, user_or_role_or_group_or_ee, permission_type_name):
        return [ pi for pi in user_or_role_or_group_or_ee.permissions if pi.get_permission_type() == permission_type_name ]

    def _get_parameter_from_permission(self, session, permission, parameter_name, default_value = DEFAULT_VALUE):
        try:
            param = [ p for p in permission.parameters if p.get_name() == parameter_name ][0]
        except IndexError:
            if default_value == DEFAULT_VALUE:
                raise DbErrors.DbIllegalStatusError(
                    permission.get_permission_type() + " permission without " + parameter_name
                )
            else:
                return default_value
        return param.value

    def _get_float_parameter_from_permission(self, session, permission, parameter_name, default_value = DEFAULT_VALUE):
        value = self._get_parameter_from_permission(session, permission, parameter_name, default_value)
        try:
            return float(value)
        except ValueError:
            raise DbErrors.InvalidPermissionParameterFormatError(
                "Expected float as parameter '%s' of '%s', found: '%s'" % (
                    parameter_name,
                    permission.get_permission_type(),
                    value
                )
            )

    def _get_int_parameter_from_permission(self, session, permission, parameter_name, default_value = DEFAULT_VALUE):
        value = self._get_parameter_from_permission(session, permission, parameter_name, default_value)
        try:
            return int(value)
        except ValueError:
            raise DbErrors.InvalidPermissionParameterFormatError(
                "Expected int as parameter '%s' of '%s', found: '%s'" % (
                    parameter_name,
                    permission.get_permission_type(),
                    value
                )
            )

    def _get_bool_parameter_from_permission(self, session, permission, parameter_name, default_value = DEFAULT_VALUE):
        return self._get_parameter_from_permission(session, permission, parameter_name, default_value)

    def _delete_all_uses(self):
        """ IMPORTANT: SHOULD NEVER BE USED IN PRODUCTION, IT'S HERE ONLY FOR TESTS """
        session = self.Session()
        try:
            uu = session.query(model.DbUserUsedExperiment).all()
            for i in uu:
                session.delete(i)
            session.commit()
        finally:
            session.close()

    def _insert_user_used_experiment(self, user_login, experiment_name, experiment_category_name, start_time, origin, coord_address, reservation_id, end_date, commands = None, files = None):
        """ IMPORTANT: SHOULD NEVER BE USED IN PRODUCTION, IT'S HERE ONLY FOR TESTS """
        if commands is None:
            commands = []

        if files is None:
            files    = []

        session = self.Session()
        try:
            user = session.query(model.DbUser).filter_by(login=user_login).one()
            category = session.query(model.DbExperimentCategory).filter_by(name=experiment_category_name).one()
            experiment = session.query(model.DbExperiment). \
                                    filter_by(name=experiment_name). \
                                    filter_by(category=category).one()
            experiment_id = experiment.id
            exp_use = model.DbUserUsedExperiment(user, experiment, start_time, origin, coord_address, reservation_id, end_date)
            session.add(exp_use)
            session.commit()
            return experiment_id
        finally:
            session.close()

    @logged()
    def retrieve_role_and_user_auths(self, username):
        """ Retrieve the role and user auths for a given username."""
        session = self.Session()
        try:
            try:
                user = session.query(model.DbUser).filter_by(login=username).one()
            except NoResultFound:
                raise DbErrors.DbUserNotFoundError("User '%s' not found in database" % username)

            all_user_auths = session.query(model.DbUserAuth).filter_by(user=user).all()
            
            # 
            sorted_user_auths = sorted(all_user_auths, lambda x, y: cmp(x.auth.priority, y.auth.priority))
            if len(sorted_user_auths) > 0:
                return user.login, user.role.name, [ user_auth.to_business() for user_auth in sorted_user_auths ]
            else:
                raise DbErrors.DbNoUserAuthNorPasswordFoundError(
                        "No UserAuth found"
                    )
        finally:
            session.close()

    @logged()
    def check_external_credentials(self, external_id, system):
        """ Given an External ID, such as the ID in Facebook or Moodle or whatever, and selecting
        the system, return the first username that matches with that user_id. The method will
        expect that the system uses something that starts by the id"""
        session = self.Session()
        try:
            try:
                auth_type = session.query(model.DbAuthType).filter_by(name=system).one()
                if len(auth_type.auths) == 0:
                    raise DbErrors.DbUserNotFoundError("No instance of system '%s' found in database." % system)
            except NoResultFound:
                raise DbErrors.DbUserNotFoundError("System '%s' not found in database" % system)

            try:
                user_auth = session.query(model.DbUserAuth).filter(model.DbUserAuth.auth_id.in_([auth.id for auth in auth_type.auths]), model.DbUserAuth.configuration==external_id).one()
            except NoResultFound:
                raise DbErrors.DbUserNotFoundError("User '%s' not found in database" % external_id)

            user = user_auth.user
            return ValidDatabaseSessionId( user.login, user.role.name)
        finally:
            session.close()

    ###########################################################################
    ##################   grant_external_credentials   #########################
    ###########################################################################
    @logged()
    def grant_external_credentials(self, username, external_id, system):
        """ Given a system and an external_id, grant access with those credentials for user user_id. Before calling
        this method, the system has checked that this user is the owner of external_id and of user_id"""
        session = self.Session()
        try:
            try:
                auth_type = session.query(model.DbAuthType).filter_by(name=system).one()
                auth = auth_type.auths[0]
            except (NoResultFound, KeyError):
                raise DbErrors.DbUserNotFoundError("System '%s' not found in database" % system)

            try:
                user = session.query(model.DbUser).filter_by(login=username).one()
            except NoResultFound:
                raise DbErrors.DbUserNotFoundError("User '%s' not found in database" % user)

            for user_auth in user.auths:
                if user_auth.auth == auth:
                    raise DbErrors.DbUserNotFoundError("User '%s' already has credentials in system %s" % (username, system))

            user_auth = model.DbUserAuth(user = user, auth = auth, configuration=str(external_id))
            session.add(user_auth)
            session.commit()
        finally:
            session.close()

    #####################################################################
    ##################   create_external_user   #########################
    #####################################################################
    @logged()
    def create_external_user(self, external_user, external_id, system, group_names):
        session = self.Session()
        try:
            try:
                auth_type = session.query(model.DbAuthType).filter_by(name=system).one()
                auth = auth_type.auths[0]
            except (NoResultFound, KeyError):
                raise DbErrors.DbUserNotFoundError("System '%s' not found in database" % system)

            groups = []
            for group_name in group_names:
                try:
                    group = session.query(model.DbGroup).filter_by(name=group_name).one()
                except NoResultFound:
                    raise DbErrors.DbUserNotFoundError("Group '%s' not found in database" % group_name)
                groups.append(group)

            try:
                role = session.query(model.DbRole).filter_by(name=external_user.role.name).one()
                user = model.DbUser(external_user.login, external_user.full_name, external_user.email, role = role)
                user_auth = model.DbUserAuth(user, auth, configuration = external_id)
                for group in groups:
                    group.users.append(user)
                session.add(user)
                session.add(user_auth)
                session.commit()
            except Exception as e:
                log.log( DatabaseGateway, log.level.Warning, "Couldn't create user: %s" % e)
                log.log_exc(DatabaseGateway, log.level.Info)
                raise DbErrors.DatabaseError("Couldn't create user! Contact administrator")
        finally:
            session.close()

    # Location updater
    @with_session
    def reset_locations_database(self):
        update_stmt = sql.update(model.DbUserUsedExperiment).values(hostname = None, city = None, most_specific_subdivision = None, country = None)
        _current.session.execute(update_stmt)
        _current.session.commit()

    @with_session
    def reset_locations_cache(self):
        _current.session.query(model.DbLocationCache).delete()
        _current.session.commit()

    @with_session
    def update_locations(self, location_func):
        """update_locations(location_func) -> number_of_updated
        
        update_locations receives a location_func which receives an IP address and
        returns the location in the following format:
        {
            'hostname': 'foo.fr', # or None
            'city': 'Bilbao', # or None
            'country': 'Spain', # or None
            'most_specific_subdivision': 'Bizkaia' # or None
        }

        If there is an error checking the data, it will simply return None.
        If the IP address is local, it will simply fill the hostname URL.

        update_locations will return the number of successfully changed registries.
        So if there were 10 IP addresses to be changed, and it failed in 5 of them,
        it will return 5. This way, the loop calling this function can sleep only if
        the number is zero.
        """
        counter = 0
        uses_without_location = list(_current.session.query(model.DbUserUsedExperiment).filter_by(hostname = None)[:1024]) # Do it iterativelly, never process more than 1024 uses
        origins = set()
        for use in uses_without_location:
            origins.add(use.origin)

        if origins:
            cached_origins = {
                # origin: result
            }
            last_month = datetime.datetime.utcnow() - datetime.timedelta(days = 31)
            for cached_origin in  _current.session.query(model.DbLocationCache).filter(model.DbLocationCache.ip.in_(origins), model.DbLocationCache.lookup_time > last_month).all():
                cached_origins[cached_origin.ip] = {
                    'city' : cached_origin.city,
                    'hostname': cached_origin.hostname,
                    'country': cached_origin.country,
                    'most_specific_subdivision' : cached_origin.most_specific_subdivision,
                }

            for use in uses_without_location:
                if use.origin in cached_origins:
                    use.city = cached_origins[use.origin]['city']
                    use.hostname = cached_origins[use.origin]['hostname']
                    use.country = cached_origins[use.origin]['country']
                    use.most_specific_subdivision = cached_origins[use.origin]['most_specific_subdivision']
                    counter += 1
                else:
                    try:
                        result = location_func(use.origin)
                    except Exception as e:
                        traceback.print_exc()
                        continue
                    use.city = result['city']
                    use.hostname = result['hostname']
                    use.country = result['country']
                    use.most_specific_subdivision = result['most_specific_subdivision']
                    cached_origins[use.origin] = result
                    new_cached_result = model.DbLocationCache(ip = use.origin, lookup_time = datetime.datetime.utcnow(), hostname = result['hostname'], city = result['city'], country = result['country'], most_specific_subdivision = result['most_specific_subdivision'])
                    _current.session.add(new_cached_result)
                    counter += 1

            try:
                _current.session.commit()
            except Exception as e:
                traceback.print_exc()

        return counter

    # Quickadmin
    def _apply_filters(self, query, query_params):
        if query_params.login:
            query = query.join(model.DbUserUsedExperiment.user).filter(model.DbUser.login == query_params.login)

        if query_params.experiment_name:
            query = query.join(model.DbUserUsedExperiment.experiment).filter(model.DbExperiment.name == query_params.experiment_name)

        if query_params.category_name:
            query = query.join(model.DbUserUsedExperiment.experiment).join(model.DbExperiment.category).filter(model.DbExperimentCategory.name == query_params.category_name)

        if query_params.group_names is not None:
            if len(query_params.group_names) == 0:
                # Automatically filter that there is no
                return query.filter(model.DbUser.login == None, model.DbUser.login != None)

            query = query.join(model.DbUserUsedExperiment.user).filter(model.DbUser.groups.any(model.DbGroup.name.in_(query_params.group_names)))

        if query_params.start_date:
            query = query.filter(model.DbUserUsedExperiment.start_date >= query_params.start_date)

        if query_params.end_date:
            query = query.filter(model.DbUserUsedExperiment.end_date <= query_params.end_date)

        return query
       
    @with_session
    def quickadmin_uses(self, limit, query_params):
        db_latest_uses_query = _current.session.query(model.DbUserUsedExperiment)

        db_latest_uses_query = self._apply_filters(db_latest_uses_query, query_params)

        db_latest_uses = db_latest_uses_query.options(joinedload("user"), joinedload("experiment"), joinedload("experiment", "category"), joinedload("properties")).order_by(model.DbUserUsedExperiment.start_date.desc()).limit(limit)

        external_user = _current.session.query(model.DbUserUsedExperimentProperty).filter_by(name = 'external_user').first()
        latest_uses = []
        for use in db_latest_uses:
            login = use.user.login
            display_name = login
            for prop in use.properties:
                if prop.property_name == external_user:
                    display_name = prop.value + u'@' + login

            latest_uses.append({
                'id' : use.id,
                'login' : login,
                'display_name' : display_name,
                'full_name' : use.user.full_name,
                'experiment_name' : use.experiment.name,
                'category_name' : use.experiment.category.name,
                'start_date' : use.start_date,
                'end_date' : use.end_date,
                'from' : use.origin,
                'city' : use.city,
                'country' : use.country,
                'hostname' : use.hostname,
            })
        return latest_uses

    @with_session
    def quickadmin_uses_per_country(self, query_params):
        db_latest_uses_query = _current.session.query(model.DbUserUsedExperiment.country, sqlalchemy.func.count(model.DbUserUsedExperiment.id))
        db_latest_uses_query = self._apply_filters(db_latest_uses_query, query_params)
        per_country = dict(db_latest_uses_query.group_by(model.DbUserUsedExperiment.country).all())
        per_country.pop(None, None)
        return per_country

    @with_session
    def quickadmin_use(self, use_id):
        use = _current.session.query(model.DbUserUsedExperiment).filter_by(id = use_id).options(joinedload("user"), joinedload("experiment"), joinedload("experiment", "category"), joinedload("properties")).first()
        if not use:
            return {'found' : False}
        
        def get_prop(prop_name, default):
            return ([ prop.value for prop in use.properties if prop.property_name.name == prop_name ] or [ default ])[0]
            
        experiment = use.experiment.name + u'@' + use.experiment.category.name

        properties = OrderedDict()
        properties['Login'] = use.user.login
        properties['Name'] = use.user.full_name
        properties['In the name of'] = get_prop('external_user', 'Himself')
        properties['Experiment'] = experiment
        properties['Date'] = use.start_date
        properties['Origin'] = use.origin
        properties['Device used'] = use.coord_address
        properties['Server IP (if federated)'] = get_prop('from_direct_ip', use.origin)
        properties['Use ID'] = use.id
        properties['Reservation ID'] = use.reservation_id
        properties['Mobile'] = get_prop('mobile', "Don't know")
        properties['Facebook'] = get_prop('facebook', "Don't know")
        properties['Referer'] = get_prop('referer', "Don't know")
        properties['Web Browser'] = get_prop('user_agent', "Don't know")
        properties['Route'] = get_prop('route', "Don't know")
        properties['Locale'] = get_prop('locale', "Don't know")
        properties['City'] = use.city or 'Unknown'
        properties['Country'] = use.country or 'Unknown'
        properties['Hostname'] = use.hostname or 'Unknown'

        commands = []
        longest_length = 0
        for command in use.commands:
            timestamp_after = command.timestamp_after
            timestamp_before = command.timestamp_before
            if timestamp_after is not None and command.timestamp_after_micro is not None:
                timestamp_after = timestamp_after.replace(microsecond = command.timestamp_after_micro)

            if timestamp_before is not None and command.timestamp_before_micro is not None:
                timestamp_before = timestamp_before.replace(microsecond = command.timestamp_before_micro)

            if timestamp_after and timestamp_before:
                length = (timestamp_after - timestamp_before).total_seconds()
                if length > longest_length:
                    longest_length = length
            else:
                length = 'N/A'
            
            commands.append({
                'length' : length,
                'before' : timestamp_before,
                'after' : timestamp_after,
                'command' : command.command,
                'response' : command.response,
            })
               
        properties['Longest command'] = longest_length

        files = []
        for f in use.files:
            timestamp_after = f.timestamp_after
            timestamp_before = f.timestamp_before
            if timestamp_after is not None and f.timestamp_after_micro is not None:
                timestamp_after = timestamp_after.replace(microsecond = f.timestamp_after_micro)

            if timestamp_before is not None and f.timestamp_before_micro is not None:
                timestamp_before = timestamp_before.replace(microsecond = f.timestamp_before_micro)

            if timestamp_after and timestamp_before:
                length = (timestamp_after - timestamp_before).total_seconds()
                if length > longest_length:
                    longest_length = length
            else:
                length = 'N/A'

            files.append({
                'file_id' : f.id,
                'length' : length,
                'before' : timestamp_before,
                'after' : timestamp_after,
                'file_info' : f.file_info,
                'file_hash' : f.file_hash,
                'response' : command.response,
            })

        return {
            'found' : True,
            'properties' : properties,
            'commands' : commands,
            'files' : files,
        }

    @with_session
    def quickadmin_filepath(self, file_id):
        use = _current.session.query(model.DbUserFile).filter_by(id = file_id).first()
        if use is None:
            return None
        initial_path = self.cfg_manager.get(configuration_doc.CORE_STORE_STUDENTS_PROGRAMS_PATH)
        if not initial_path:
            return None
        full_path = os.path.join(initial_path, use.file_sent)
        if not os.path.exists(full_path):
            return None

        return full_path

def create_gateway(cfg_manager):
    return DatabaseGateway(cfg_manager)


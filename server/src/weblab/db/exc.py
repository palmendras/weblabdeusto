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
#         Luis Rodriguez <luis.rodriguez@opendeusto.es>
# 
import weblab.exc as wlExc

class DatabaseException(wlExc.WebLabException):
    def __init__(self,*args,**kargs):
        wlExc.WebLabException.__init__(self,*args,**kargs)

class DbInvalidUserOrPasswordException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbUserNotFoundException(DbInvalidUserOrPasswordException):
    def __init__(self,*args,**kargs):
        DbInvalidUserOrPasswordException.__init__(self,*args,**kargs)

class DbProvidedUserNotFoundException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)
        
class DbProvidedGroupNotFoundException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbHashAlgorithmNotFoundException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbInvalidPasswordFormatException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbIllegalStatusException(DatabaseException):
    def __init__(self,*args,**kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbMisconfiguredException(DatabaseException):
    def __init__(self, *args, **kargs):
        DatabaseException.__init__(self,*args,**kargs)
        
class InvalidPermissionParameterFormatException(DatabaseException):
    def __init__(self, *args, **kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbProvidedExperimentNotFoundException(DatabaseException):
    def __init__(self, *args, **kargs):
        DatabaseException.__init__(self,*args,**kargs)

class DbUserAuthException(DatabaseException):
    def __init__(self, *args, **kargs):
        DatabaseException.__init__(self, *args, **kargs)

class DbUnsupportedUserAuth(DbUserAuthException):
    def __init__(self, *args, **kargs):
        DbUserAuthException.__init__(self, *args, **kargs)

class DbInvalidUserAuthConfigurationException(DbUserAuthException):
    def __init__(self, *args, **kargs):
        DbUserAuthException.__init__(self, *args, **kargs)

class DbNoUserAuthNorPasswordFoundException(DbUserAuthException):
    def __init__(self, *args, **kargs):
        DbUserAuthException.__init__(self, *args, **kargs)


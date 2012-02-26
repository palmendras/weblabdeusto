from collections import namedtuple

NO_DEFAULT = object()
ANY_TYPE   = object()

_Argument = namedtuple('Argument', 'category type default message')

_sorted_variables = []


######################################
# 
# COMMON
# 

COMMON = 'Common configuration'

# 
# General
# 

GENERAL = (COMMON, 'General')

DEBUG_MODE                        = 'debug_mode'
SERVER_ADMIN                      = 'server_admin'
PROPAGATE_STACK_TRACES_TO_CLIENT  = 'propagate_stack_traces_to_client'
FACADE_TIMEOUT                    = 'facade_timeout'
SERVER_HOSTADDRESS                = 'server_hostaddress'

_sorted_variables.extend([
    (DEBUG_MODE,                       _Argument(GENERAL, bool,  False,      "If True, errors and exceptions are shown instead of generic feedback (like !WebLabInternalServerError)")),
    (SERVER_ADMIN,                     _Argument(GENERAL, str,   None,       "!WebLab-Deusto administrator's email address for notifications. See Admin Notifier settings below.")),
    (SERVER_HOSTADDRESS,               _Argument(GENERAL, str,   '',         "Host address of this WebLab-Deusto deployment")),
    (PROPAGATE_STACK_TRACES_TO_CLIENT, _Argument(GENERAL, bool,  False,      "If True, stacktraces are propagated to the client (useful for debugging).")),
    (FACADE_TIMEOUT,                   _Argument(GENERAL, float, 0.5,        "Seconds that the facade will wait accepting a connection before checking again for shutdown requests.")),
])

# 
# Admin notifier
# 

ADMIN_NOTIFIER = (COMMON, 'Admin Notifier')

MAIL_NOTIFICATION_ENABLED = 'mail_notification_enabled'
MAIL_SERVER_HOST          = 'mail_server_host'
MAIL_SERVER_HELO          = 'mail_server_helo'
MAIL_SERVER_USE_TLS       = 'mail_server_use_tls'
MAIL_NOTIFICATION_SENDER  = 'mail_notification_sender'
MAIL_NOTIFICATION_SUBJECT = 'mail_notification_subject'

_sorted_variables.extend([
    (MAIL_NOTIFICATION_ENABLED, _Argument(ADMIN_NOTIFIER, bool, NO_DEFAULT, "Enables or Disables mail notifications")),
    (MAIL_SERVER_HOST,          _Argument(ADMIN_NOTIFIER, str,  NO_DEFAULT, "Host to use for sending mail")),
    (MAIL_SERVER_HELO,          _Argument(ADMIN_NOTIFIER, str,  NO_DEFAULT, "Address to be used on the mail's HELO")),
    (MAIL_SERVER_USE_TLS,       _Argument(ADMIN_NOTIFIER, str,  'no',       "Use TLS or not. Values: 'yes' or 'no'")),
    (MAIL_NOTIFICATION_SENDER,  _Argument(ADMIN_NOTIFIER, str,  NO_DEFAULT, "Address of the mail's sender")), 
    (MAIL_NOTIFICATION_SUBJECT, _Argument(ADMIN_NOTIFIER, str,  "[WebLab] CRITICAL ERROR!", "(Optional) Subject of the notification mail")),
])

# 
# Database 
#

DATABASE = (COMMON, 'Database')

DB_HOST                         = 'db_host'
DB_DATABASE                     = 'db_database'
DB_ENGINE                       = 'db_engine'
WEBLAB_DB_USERNAME              = 'weblab_db_username'
WEBLAB_DB_PASSWORD              = 'weblab_db_password'
WEBLAB_DB_FORCE_ENGINE_CREATION = 'weblab_db_force_engine_creation'

_sorted_variables.extend([
    (DB_HOST,                         _Argument(DATABASE, str,  'localhost', "Location of the database server")),
    (DB_DATABASE,                     _Argument(DATABASE, str,  'WebLab',    "Name of the main database")),
    (DB_ENGINE,                       _Argument(DATABASE, str,  'mysql',     "Engine used. Example: mysql, sqlite")),
    (WEBLAB_DB_USERNAME,              _Argument(DATABASE, str,  "weblab",    "WebLab database username")),
    (WEBLAB_DB_PASSWORD,              _Argument(DATABASE, str,  NO_DEFAULT,  "WebLab database user password")),
    (WEBLAB_DB_FORCE_ENGINE_CREATION, _Argument(DATABASE, bool, False,       "Force the creation of an engine each time")),
])

# 
# Sessions
# 

SESSIONS = (COMMON, 'Sessions')

SESSION_LOCKER_MYSQL_HOST                 = 'session_locker_mysql_host'
SESSION_LOCKER_MYSQL_DB_NAME              = 'session_locker_mysql_db_name'
SESSION_LOCKER_MYSQL_USERNAME             = 'session_locker_mysql_username'
SESSION_LOCKER_MYSQL_PASSWORD             = 'session_locker_mysql_password'
SESSION_LOCKER_MYSQL_CONNECTION_POOL_SIZE = 'session_locker_mysql_connection_pool_size'


# ==== Sessions ====
# 
# !WebLab-Deusto supports two types of Session Managers:
#  * "Memory", storing all the sessions in memory. Fastest.
#  * "MySQL", storing all the sessions in MySQL tables. Far slower, but it can be shared among two servers to provide fault tolerance.
# 
# || *Property* || *Type* || *Default value* || *Description* || 
# || session_locker_mysql_host || str || "localhost" || Location of the locking database server || 
# || session_locker_mysql_db_name || str || "!WebLabSessions" || Database name of the locking database || 
# || session_locker_mysql_username || str ||  || Username for connecting to the locking database || 
# || session_locker_mysql_password || str ||  || Password for connecting to the locking database || 
# || session_locker_mysql_connection_pool_size || int || 25 || Maximum number of concurrent connections to the locking database per process || 
# || session_locker_mysql_connection_timeout || int || 60 || In seconds, how long will the server wait for connecting to the locking database || 
# || session_manager_default_timeout || int || 3600 `*` 2 || Maximum time that a session will be stored in a Session Manager. In seconds. || 
# || session_memory_gateway_serialize || bool || False || Sessions can be stored in a database or in memory. If they are stored in memory, they can be serialized in memory or not, to check the behaviour || 


######################################
# 
# CORE SERVER
#

CORE_SERVER = 'Core Server'


CORE = (CORE_SERVER,'General')

WEBLAB_CORE_SERVER_SESSION_TYPE     = 'core_session_type'
WEBLAB_CORE_SERVER_SESSION_POOL_ID  = 'core_session_pool_id'

_sorted_variables.extend([
    (WEBLAB_CORE_SERVER_SESSION_TYPE,    _Argument(CORE, str, 'Memory', """What type of session manager the Core Server will use: Memory or MySQL.""")),
    (WEBLAB_CORE_SERVER_SESSION_POOL_ID, _Argument(CORE, str, 'UserProcessingServer', """ A unique identifier of the type of sessions, in order to manage them. For instance, if there are four servers (A, B, C and D), the load of users can be splitted in two groups: those being sent to A and B, and those being sent to C and D. A and B can share those sessions to provide fault tolerance (if A falls down, B can keep working from the same point A was) using a MySQL session manager, and the same may apply to C and D. The problem is that if A and B want to delete all the sessions -at the beginning, for example-, but they don't want to delete sessions of C and D, then they need a unique identifier shared for A and B, and another for C and D. In this case, "!UserProcessing_A_B" and "!UserProcessing_C_D" would be enough.""")),
])

#####################################
# 
# The rest
# 


variables = dict(_sorted_variables)

if __name__ == '__main__':
    categories = set([ variable.category for variable in variables.values() ])
    variables_by_category = {}

    sections = {}

    for category in categories:
        section, subsection = category
        subsections = sections.get(section, set())
        subsections.add(subsection)
        sections[section] = subsections
        variables_by_category[category] = [ variable for variable in variables if variables[variable].category == category ]

    for section in sections:
        print ' '.join(('=' * 3,section,'=' * 3))
        print
        for subsection in sections[section]:
            print ' '.join(('=' * 4,subsection,'=' * 4))
            print
            category = (section, subsection)
            print "|| *Property* || *Type* || *Default value* || *Description* ||"
            for variable, argument in _sorted_variables:
                if variable in variables_by_category[category]:
                    print "|| %(variable)s || %(type)s || %(default)s || %(doc)s ||" % {
                                        'variable' : variable,
                                        'type'     : variables[variable].type.__name__,
                                        'default'  : variables[variable].default if variables[variable].default is not NO_DEFAULT else '',
                                        'doc'      : variables[variable].message
                                    }
            print


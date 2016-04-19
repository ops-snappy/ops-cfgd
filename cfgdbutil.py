#!/usr/bin/env python
# (C) Copyright 2015 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



from opsrest.settings import settings
import ops.dc
from opslib import restparser

import base64
import getopt
import os
import json
import sys

import ovs.dirs
from ovs.db import error
from ovs.db import types
import ovs.poller
import ovs.db.idl
import cfgdb

type_startup_config = "startup"

vlog = ovs.vlog.Vlog("cfgmgmt")
TEMPORARY_DB_SHOW_STARTUP = "unix:/var/run/openvswitch/temp_startup.sock"


def show_config(args):
    ret = True
    if (args[0] != "startup-config"):
        print("Unknown config \"%s\" (Use --help for help)" % args[0])
        return False

    cfg = cfgdb.Cfgdb()

    #OPS TODO: To get confg type from user as args
    row, tbl_found = cfg.find_row_by_type("startup")

    if tbl_found:
        try:
            data = json.loads(base64.b64decode(row.config))
            print("Startup configuration:")
            if (args[1] == "json"):
                print json.dumps(data,  indent=4, sort_keys=True)
            elif (args[1] == "cli"):
                # Here we copy saved configuration from config DB to temporary
                # DB and the current startup configuration command displays
                # output by traversing the temporary DB.
                extschema = restparser.parseSchema(settings.get('ext_schema'))
                ovsschema = settings.get('ovs_schema')
                ovsremote = TEMPORARY_DB_SHOW_STARTUP

                # initialize idl
                opsidl = ops.dc.register(extschema, ovsschema, ovsremote)
                curr_seqno = opsidl.change_seqno
                while True:
                    opsidl.run()
                    if curr_seqno != opsidl.change_seqno:
                        break
                    poller = ovs.poller.Poller()
                    opsidl.wait(poller)
                    poller.block()

                # write to db
                txn = ovs.db.idl.Transaction(opsidl)
                result = ops.dc.write(data, extschema, opsidl, txn)
                if result == ovs.db.idl.Transaction.INCOMPLETE:
                    result = txn.commit_block()

                if result not in [ovs.db.idl.Transaction.SUCCESS, ovs.db.idl.Transaction.UNCHANGED]:
                    print("Transaction result %s" %result)
                    return False

        except ValueError, e:
            print("Invalid json from configdb. Exception: %s\n" % e)
            ret = False
    else:
        print('No saved configuration exists')
        ret = False

    cfg.close()
    return ret


def copy_running_startup():

    # get running config
    extschema = restparser.parseSchema(settings.get('ext_schema'))
    ovsschema = settings.get('ovs_schema')
    ovsremote = settings.get('ovs_remote')

    # initialize idl
    opsidl = ops.dc.register(extschema, ovsschema, ovsremote)
    curr_seqno = opsidl.change_seqno
    while True:
        opsidl.run()
        if curr_seqno != opsidl.change_seqno:
            break
        poller = ovs.poller.Poller()
        opsidl.wait(poller)
        poller.block()

    running_config = ops.dc.read(extschema, opsidl)

    # base64 encode to save as startup
    config = base64.b64encode(json.dumps(running_config))
    cfg = cfgdb.Cfgdb()
    cfg.config = config
    cfg.type = "startup"
    row, tbl_found = cfg.find_row_by_type("startup")
    if tbl_found:
        cfg.update_row(row)
    else:
        cfg.insert_row()

    cfg.close()
    return True


def copy_startup_running():
    cfg = cfgdb.Cfgdb()

    #OPS TODO: To get confg type from user as args
    row, tbl_found = cfg.find_row_by_type("startup")

    if tbl_found:
        try:
            data = json.loads(base64.b64decode(row.config))
        except ValueError, e:
            print("Invalid json from configdb. Exception: %s\n" % e)
            cfg.close()
            return False
    else:
        print('No saved configuration exists')
        cfg.close()
        return False

    extschema = restparser.parseSchema(settings.get('ext_schema'))
    ovsschema = settings.get('ovs_schema')
    ovsremote = settings.get('ovs_remote')

    # initialize idl
    opsidl = ops.dc.register(extschema, ovsschema, ovsremote)
    curr_seqno = opsidl.change_seqno
    while True:
        opsidl.run()
        if curr_seqno != opsidl.change_seqno:
            break
        poller = ovs.poller.Poller()
        opsidl.wait(poller)
        poller.block()

    txn = ovs.db.idl.Transaction(opsidl)
    result = ops.dc.write(data, extschema, opsidl, txn)
    if result == ovs.db.idl.Transaction.INCOMPLETE:
        result = txn.commit_block()

    if result not in [ovs.db.idl.Transaction.SUCCESS, ovs.db.idl.Transaction.UNCHANGED]:
        return False

    return True


def copy_config(args):
    ret = True
    if (args[0] == "running-config" and args[1] == "startup-config"):
        ret = copy_running_startup()
    elif (args[0] == "startup-config" and args[1] == "running-config"):
        ret = copy_startup_running()
    else:
        print("Unknow config (use --help for help)")
        ret = False
    return ret


def delete_config(args):
    if (args[0] != "startup-config"):
        print("Unknown config \"%s\" (Use --help for help)" % args[0])
        return False

    cfg = cfgdb.Cfgdb()

    #OPS TODO: To get confg type from user from user as args
    status, tbl_found = cfg.delete_row_by_type("startup")

    if tbl_found:
        print("Delete statup row status : %s" % status)
    else:
        print('No saved configuration exists')
        cfg.close()
        return False

    cfg.close()
    return True


def usage(name):
    print (
        "%s: Configuration Persistance Utility \n\
        usage: %s [--help] COMMAND ARG...\n\n\
        The following commands are supported: \n\n\
        show startup-config cli\n\
            Shows the contentes of startup configuration in CLI format\n\n\
        show startup-config json\n\
            Shows the contentes of startup configuration in JSON\n\n\
        copy running-config startup-config \n\
            Copy running config to startup config \n\n\
        copy start-config running-config \n\
            Copy startup config to running config)\n\n\
        delete startup-config \n\
            Delete the startup configuration row in configdb\n\n"
        % (name, name))


def main():
    argv = sys.argv
    program_name = argv[0]

    try:
        options, args = getopt.gnu_getopt(argv[1:], 'h', ['help'])
    except getopt.GetoptError, geo:
        print("%s: %s\n" % (program_name, geo.msg))
        sys.exit(2)

    for key, value in options:
        if key in ['-h', '--help']:
            usage(program_name)
            sys.exit(0)

    if not args:
        print("%s: missing command argument (use --help for help)\n"
              % program_name)
        sys.exit(2)

    #Command Dictionary with command name as key and key value as list
    #with functions and corresponding argument length
    commands = {"show":   (show_config, 2),
                "copy":   (copy_config, 2),
                "delete": (delete_config, 1)}

    command_name = args[0]
    args = args[1:]

    if not command_name in commands:
        print("%s: unknown command \'%s\' (use --help for help)\n"
              % (program_name, command_name))
        sys.exit(2)

    func, n_args = commands[command_name]
    if type(n_args) == tuple:
        if len(args) < n_args[0]:
            print("%s: \"%s\" requires at least %d arguments but "
                  "only %d provided (use --help for help)\n"
                  % (program_name, command_name, n_args, len(args)))
            sys.exit(2)
    elif type(n_args) == int:
        if len(args) != n_args:
            print("%s: \"%s\" requires %d arguments but %d provided "
                  "(use --help for help)\n"
                  % (program_name, command_name, n_args, len(args)))
            sys.exit(2)
    else:
        assert False, ("Invalid argument length %s %s" % (func, n_args))

    if func(args) is False:
        sys.exit(2)

if __name__ == '__main__':
    try:
        main()
    except error.Error, e:
        print("Error: \"%s\" \n" % e)

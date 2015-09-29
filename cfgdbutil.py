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

from runconfig.runconfig import RunConfigUtil
from opsrest.settings import settings
from opsrest.manager import OvsdbConnectionManager
from opslib import restparser

import getopt
import os
import json
import sys
import time

import ovs.dirs
from ovs.db import error
from ovs.db import types
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
            # Here we copy saved configuration from config DB to temporary DB
            # and the current startup configuration command displays output
            # by traversing the temporary DB.
            parsed = json.loads(row.config)
            print("Startup configuration:")
            manager = OvsdbConnectionManager(TEMPORARY_DB_SHOW_STARTUP,
                                             settings.get('ovs_schema'))
            manager.start()
            cnt = 30
            while not manager.idl.run() and cnt > 0:
                time.sleep(.1)
                cnt -= 1
            if cnt <= 0:
                print("IDL connection timeout")
                return False
            # read the schema
            schema = restparser.parseSchema(settings.get('ext_schema'))
            run_config_util = RunConfigUtil(manager.idl, schema)
            run_config_util.write_config_to_db(parsed)
            manager.idl.close()

        except ValueError, e:
            print("Invalid json from configdb. Exception: %s\n" % e)
            ret = False
    else:
        print('No saved configuration exists')
        ret = False

    cfg.close()
    return ret


def copy_running_startup():
    cfg = cfgdb.Cfgdb()
    manager = OvsdbConnectionManager(settings.get('ovs_remote'),
                                     settings.get('ovs_schema'))
    manager.start()
    idl = manager.idl

    init_seq_no = idl.change_seqno
    # Wait until the connection is ready
    while True:
        idl.run()
        # print self.idl.change_seqno
        if init_seq_no != idl.change_seqno:
            break
        time.sleep(1)

    restschema = restparser.parseSchema(settings.get('ext_schema'))

    run_config_util = RunConfigUtil(idl, restschema)
    config = run_config_util.get_running_config()

    cfg.config = ovs.json.to_string(config)
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
            data = json.loads(row.config)
        except ValueError, e:
            print("Invalid json from configdb. Exception: %s\n" % e)
            cfg.close()
            return False
    else:
        print('No saved configuration exists')
        cfg.close()
        return False

    # set up IDL
    manager = OvsdbConnectionManager(settings.get('ovs_remote'),
                                     settings.get('ovs_schema'))
    manager.start()
    init_seq_no = manager.idl.change_seqno
    while True:
        manager.idl.run()
        if init_seq_no != manager.idl.change_seqno:
            break
        time.sleep(1)

    # read the schema
    schema = restparser.parseSchema(settings.get('ext_schema'))
    run_config_util = RunConfigUtil(manager.idl, schema)
    run_config_util.write_config_to_db(data)
    cfg.close()
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
        show startup-config \n\
            Shows the contentes of startup configuration \n\n\
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
    commands = {"show":   (show_config, 1),
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

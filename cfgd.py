#!/usr/bin/env python
# (C) Copyright 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import sys
import argparse
import json
from time import sleep

import ovs.dirs
from ovs.db import error
from ovs.db import types
import ovs.util
import ovs.daemon
import ovs.db.idl
import ovs.unixctl
import ovs.unixctl.server
import ovs.vlog

from runconfig.runconfig import RunConfigUtil
from halonrest.settings import settings
from halonrest.manager import OvsdbConnectionManager
from halonlib import restparser

# ovs definitions
idl = None
# OPS_TODO: Need to pull this from the build env
def_db = 'unix:/var/run/openvswitch/db.sock'

# Configuration file definitions
saved_config = None
# OPS_TODO: Need to pull these three from the build env
cfgdb_schema = '/usr/share/openvswitch/configdb.ovsschema'
ovs_schema = '/usr/share/openvswitch/vswitch.ovsschema'
type_startup_config = "startup"
#3 sec max retry
max_miliseconds_to_wait_for_config_data = 30

# Program control
exiting = False
loop_seq_no = 0
dispatch_list = []

# VLOG
vlog = ovs.vlog.Vlog("cfgd")


#####################  OVS Methods ######################

#------------------ unixctl_exit() ----------------
def unixctl_exit(conn, unused_argv, unused_aux):
    global exiting

    exiting = True
    conn.reply(None)


#------------------ db_is_cur_cfg_set() ----------------
def db_is_cur_cfg_set(data):
    '''
    Check to see if the System:cur_cfg value exists and is > 0
    '''

    for ovs_rec in data["System"].rows.itervalues():
        if ovs_rec.cur_cfg:
            if ovs_rec.cur_cfg > 0:
                return True
            else:
                return False

    return False


#------------------ db_get_hw_done() ----------------
def db_get_hw_done(data):
    '''
    Check to see if the System:cur_hw value exists and is > 0
    '''

    for ovs_rec in data["System"].rows.itervalues():
        if ovs_rec.cur_hw:
            if ovs_rec.cur_hw == 0:
                return False
            else:
                return True

    return False


#------------------ wait_for_hw_done() ----------------
def wait_for_hw_done():
    '''
    Check db to see if h/w initialization has completed.
    If true: return True
    else: return False
    '''

    global idl

    # Check db to see if cfgd has already run.
    if db_is_cur_cfg_set(idl.tables):
        vlog.info("cur_cfg already set...cfgd exiting")
        return terminate()

    # Check db to see if h/w initialization has completed.

    if db_get_hw_done(idl.tables):
        return True
    else:
        # Delay a little before trying again
        sleep(0.2)
        return False


#------------------ get_config() ----------------
def get_config(idl_cfg):
    '''
    Walk through the rows in the config table (if any)
    looking for a row with type == startup.

    If found, set global variable saved_config to the content
    of the "config" field in that row.
    '''

    global saved_config

    #Note: You can't tell the difference between the config table not
    #      existing (that is the configdb is not there) or just that there
    #      are no rows in the config table.
    tbl_found = False
    for ovs_rec in idl_cfg.tables["config"].rows.itervalues():
        tbl_found = True
        if ovs_rec.type:
            if ovs_rec.type == type_startup_config:
                if ovs_rec.config:
                    saved_config = ovs_rec.config
                else:
                    vlog.warn("startup config row does not have config column")
                return

    if not tbl_found:
        vlog.info("No rows found in the config table")


#------------------ check_for_startup_config() ----------------
def check_for_startup_config(remote):
    '''
    Connect to the db server and specify the configdb database.
    Look for an entry with type=startup
    If exists, read the configuration.
    '''

    global saved_config

    saved_config = None

    schema_helper_cfg = ovs.db.idl.SchemaHelper(location=cfgdb_schema)
    schema_helper_cfg.register_table("config")

    idl_cfg = ovs.db.idl.Idl(remote, schema_helper_cfg)

    # Take a pass at the db to get any config data
    # Note: idl.run() function returns true when seqno changes
    cnt = max_miliseconds_to_wait_for_config_data
    while not idl_cfg.run() and cnt > 0:
        cnt -= 1
        sleep(.1)

    get_config(idl_cfg)

    idl_cfg.close()

    return


#####################  Utility Methods ######################
#------------------ push_config_to_db() ----------------
def push_config_to_db():
    '''
    Take the previously discovered startup configuration and
    push it to the database.
    '''

    global saved_config

    if saved_config is None:
        vlog.info('No saved configuration exists')
    else:
        #OPS_TODO: Change this log msg to the actual push code when available
        vlog.info('Config data found')
        try:
            data = json.loads(saved_config)
        except ValueError, e:
            print("Invalid json from configdb. Exception: %s\n" % e)
            return

        # set up IDL
        manager = OvsdbConnectionManager(settings.get('ovs_remote'),
                                         settings.get('ovs_schema'))
        manager.start()
        manager.idl.run()

        init_seq_no = manager.idl.change_seqno
        while True:
            manager.idl.run()
            if init_seq_no != manager.idl.change_seqno:
                break
            sleep(1)

        # read the schema
        schema = restparser.parseSchema(settings.get('ext_schema'))
        run_config_util = RunConfigUtil(manager.idl, schema)
        run_config_util.write_config_to_db(data)

    return True


#------------------ mark_completion() ----------------
def mark_completion():
    '''
    set "config done" in db.
    '''

    global idl

    # create the transaction
    seqno = idl.change_seqno
    txn = ovs.db.idl.Transaction(idl)

    # modify the values
    for ovs_rec in idl.tables["System"].rows.itervalues():
        ovs_rec.cur_cfg += 1
        ovs_rec.next_cfg = ovs_rec.cur_cfg

    # commit the transaction
    if txn.commit_block() != ovs.db.idl.Transaction.SUCCESS:
        return False

    return True


#------------------ terminate() ----------------
def terminate():
    global exiting

    exiting = True
    return True


###################  Main Loop Serializing Methods ###############
def init_dispatcher():
    '''
    Creates a list of functions to call in sequence
    Initializes loop_seq_no to zero.
    '''

    global dispatch_list
    global loop_seq_no
    global exiting

    dispatch_list = []

    # Each of these functions must return:
    #   True if the function has completed its job, or
    #   False if it needs to run again

    dispatch_list.append(wait_for_hw_done)
    dispatch_list.append(push_config_to_db)
    dispatch_list.append(mark_completion)
    dispatch_list.append(terminate)

    loop_seq_no = 0


def dispatcher():
    '''
    Call next funtion in the list
    If it returns true, increment the loop counter
    If run out of functions, terminate
    '''

    global dispatch_list
    global loop_seq_no
    global exiting

    if loop_seq_no < len(dispatch_list):
        rc = dispatch_list[loop_seq_no]()
        if rc:
            loop_seq_no += 1
    else:
        exiting = True


###############################  main  ###########################
def main():
    '''cfgd.main()

    cfgd processing logic is:

    create IDL session to configdb
    if row with type=startup exists, save off the config data
    close configdb IDL session

    start main loop and call functions to...
        wait for h/w initialization to complete
        if default config (see above), push the config to the db.
        mark configuration completion in the db.
        terminate
    '''

    global exiting
    global idl
    global loop_seq_no

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database', metavar="DATABASE",
                        help="A socket on which ovsdb-server is listening.",
                        dest='database')

    ovs.vlog.add_args(parser)
    ovs.daemon.add_args(parser)
    args = parser.parse_args()
    ovs.vlog.handle_args(args)
    ovs.daemon.handle_args(args)

    if args.database is None:
        remote = def_db
    else:
        remote = args.database

    # Locate default config if it exists
    check_for_startup_config(remote)

    schema_helper = ovs.db.idl.SchemaHelper(location=ovs_schema)
    schema_helper.register_columns("System",
                                   ["cur_hw", "cur_cfg", "next_cfg"])

    idl = ovs.db.idl.Idl(remote, schema_helper)

    ovs.daemon.daemonize()

    ovs.unixctl.command_register("exit", "", 0, 0, unixctl_exit, None)
    error, unixctl_server = ovs.unixctl.server.UnixctlServer.create(None)
    if error:
        ovs.util.ovs_fatal(error, "could not create unixctl server", vlog)

    seqno = idl.change_seqno    # Sequence number when we last processed the db

    init_dispatcher()

    while not exiting:
        # See if we have an incoming command
        unixctl_server.run()
        if exiting:
            break

        # Take a pass at the db to see if anything has come in
        idl.run()

        # Keeping this here for later when we don't terminate.
        '''
        # OPS_TODO: when we want to keep cfgd running, add code
        # ...to know when the dispatcher is through and then start
        # ...using this code to block on a db change.
        if seqno == idl.change_seqno:
            poller = ovs.poller.Poller()
            unixctl_server.wait(poller)
            idl.wait(poller)
            poller.block()
        '''

        # Call next method in the sequence
        dispatcher()

        seqno = idl.change_seqno

    unixctl_server.close()
    idl.close()

    return

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        # Let system.exit() calls complete normally
        raise
    except:
        vlog.exception("traceback")
        sys.exit(ovs.daemon.RESTART_EXIT_CODE)

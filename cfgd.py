#!/usr/bin/env python
# Copyright (C) 2014-2015 Hewlett-Packard Development Company, L.P.
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

# ovs definitions
idl = None
# HALON_TODO: Need to pull this from the build env
def_db = 'unix:/var/run/openvswitch/db.sock'

# Configuration file definitions
CONFIG_FILE_DIR = '/var/local/config/'
USER_FILE = CONFIG_FILE_DIR + 'user.cfg'
STARTUP_FILE = CONFIG_FILE_DIR + 'startup.cfg'
FACTORY_FILE = CONFIG_FILE_DIR + '.factory.cfg'
CONFIG_FILE_SEARCH_LIST = [USER_FILE, STARTUP_FILE, FACTORY_FILE]

'''
# HALON_TODO: Remove if we decide to not use linux files.
cfg_filep = None
cfg_name = None
'''

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

#------------------ db_get_hw_done() ----------------
def db_get_hw_done(data):
    '''
    Check to see if the Open_vSwitch:cur_hw value exists and is > 0
    '''

    for ovs_rec in data["Open_vSwitch"].rows.itervalues():
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

    # Check db to see if h/w initialization has completed.

    if db_get_hw_done(idl.tables):
        return True
    else:
        # Delay a little before trying again
        sleep(0.2)
        return False



#####################  Utility Methods ######################

#------------------ check_for_default_config() ----------------
def check_for_default_config():

    '''
    # HALON_TODO: Remove if we decide to not use linux files.
    for name in CONFIG_FILE_SEARCH_LIST:
        if os.path.isfile(name):
            try:
                f = open(name, 'r')
            except Exception as e:
                vlog.err('config file open failed for {0}, e={1}' \
                            .format(name, e))
                return None, None
            return f, name

    return None, None
    '''

    pass

#------------------ push_config_to_db() ----------------
def push_config_to_db():
    '''
    Take the previously discovered default configuration and
    push it to the database.
    '''

    '''
    # HALON_TODO: Remove if we decide to not use linux files.
    # This is older code that pulls the config from a file.
    global cfg_filep, cfg_name


    if cfg_filep is None:
        vlog.info('No configuration to push')
        return True

    try:
        config = json.load(cfg_filep)
    except Exception as e:
        vlog.err('config file read failed for {0}, e={1}'.format(cfg_name, e))
        raise e

    try:
        # HALON_TODO: Call goes here to push config to db
        pass
    except Exception as e:
        vlog.err('config push to db failed, e={0}'.format(e))
        raise e
    '''

    vlog.info('No configuration to push')

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
    for ovs_rec in idl.tables["Open_vSwitch"].rows.itervalues():
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

    # HALON_TODO: Remove if we decide to not use linux files.
    ### this is the old way....###
    locate configuration file to use. Search in the following order...
        1st - User default config : /var/local/config/user.cfg
        2nd - User startup config : /var/local/config/startup.cfg
        3rd - Factory default config: /var/local/config/.factory.cfg

    # HALON_TODO: Keep if we decide to use a cfg db.
    ### the new way is....###
    connect to the cfg db
    locate the row marked as default (if exists)

    start main loop and call functions to...
        wait for h/w initialization to complete
        if default config found, push the config to the db.
        mark configuration completion in the db.
        terminate

    In the future, cfgd will not terminate. It will continue to
    watch for configuration changes and then mark configuration done
    when all config daemons indicate they are done.
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

    schema_helper = ovs.db.idl.SchemaHelper()

    # This is here as reference....need to remove at some point.
    #schema_helper.register_columns("Interface", ["name", "type", "options"])

    schema_helper.register_columns("Open_vSwitch", \
            ["cur_hw", "cur_cfg", "next_cfg"])

    idl = ovs.db.idl.Idl(remote, schema_helper)

    ovs.daemon.daemonize()

    ovs.unixctl.command_register("exit", "", 0, 0, unixctl_exit, None)
    error, unixctl_server = ovs.unixctl.server.UnixctlServer.create(None)
    if error:
        ovs.util.ovs_fatal(error, "could not create unixctl server", vlog)

    seqno = idl.change_seqno    # Sequence number when we last processed the db

    # Locate default config if it exists
    check_for_default_config()

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
        # HALON_TODO: when we want to keep cfgd running, add code
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

#!/usr/bin/python
# Copyright (C) 2014-2015 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
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
import time
#import json
#import subprocess

if 'BUILD_ROOT' in os.environ:
    BUILD_ROOT = os.environ['BUILD_ROOT']
else:
    BUILD_ROOT = "../../.."

HALON_VSI_LIB = BUILD_ROOT + "/src/halon-vsi"
sys.path.append(HALON_VSI_LIB)

import mininet
from halonvsi.docker import *
from halonvsi.halon import *


#OVS_VSCTL = "/usr/bin/ovs-vsctl "

ALL_DAEMONS = "sysd pmd tempd powerd ledd fand cfgd switchd intfd vland lacpd lldpd zebra bgpd ovsdb-server"
PLATFORM_DAEMONS = "sysd pmd tempd powerd ledd fand"
CREATE_OVSDB_CMD = "/usr/bin/ovsdb-tool create /var/run/openvswitch/ovsdb.db /usr/share/openvswitch/vswitch.ovsschema"
CREATE_CONFIGDB_CMD = "/usr/bin/ovsdb-tool create /var/local/openvswitch/config.db /usr/share/openvswitch/configdb.ovsschema"
OVSDB_STARTUP_CMD_NORMAL = "/usr/sbin/ovsdb-server --remote=punix:/var/run/openvswitch/db.sock --detach --no-chdir --pidfile -vSYSLOG:INFO /var/run/openvswitch/ovsdb.db /var/local/openvswitch/config.db"
OVSDB_STARTUP_CMD_NO_CONFIGDB = "/usr/sbin/ovsdb-server --remote=punix:/var/run/openvswitch/db.sock --detach --no-chdir --pidfile -vSYSLOG:INFO /var/run/openvswitch/ovsdb.db"
OVSDB_STOP_CMD = "kill -9 `cat /var/run/openvswitch/ovsdb-server.pid`"
CFGD_CMD = "/usr/bin/cfgd"
CFG_TBL_NOT_FOUND_MSG = "No rows found in the config table"
CFG_DATA_FOUND_MSG = "Config data found"
CUR_CFG_SET_MSG = "cur_cfg already set"
OVSDB = "/var/run/openvswitch/ovsdb.db"
CONFIGDB = "/var/local/openvswitch/config.db"
OVSDB_CLIENT_TRANSACT_CMD = "/usr/bin/ovsdb-client -v transact "
ADD_STARTUP_ROW_FILE = "add_startup_row"
ADD_TEST_ROW_FILE = "add_test_row"
GET_OPEN_VSWITCH_TABLE_CMD = "ovs-vsctl list open_vswitch"

'''
For now, only one function by the name of test is supported. To enable
multiple tests I wrote separate functions for each test and call them from the
main test function.
'''


class cfgdTest( HalonTest ):


    def setupNet(self):
        # if you override this function, make sure to
        # either pass getNodeOpts() into hopts/sopts of the topology that
        # you build or into addHost/addSwitch calls
        self.net = Mininet(topo=SingleSwitchTopo(
            k=1,
            hopts=self.getHostOpts(),
            sopts=self.getSwitchOpts()),
            switch=HalonSwitch,
            host=HalonHost,
            link=HalonLink,
            controller=None,
            build=True)

    def stop_daemon(self, switch, daemon):
        debug(switch.cmd("/bin/systemctl stop " + daemon))

    def start_daemon(self, switch, daemon):
        debug(switch.cmd("/bin/systemctl start " + daemon))

    def remove_db(self, switch, db):
        debug(switch.cmd("/bin/rm -f " + db))

    def create_db(self, switch, db):
        debug(switch.cmd(db))

    def rebuild_dbs(self, switch):
        debug(self.remove_db(switch, OVSDB))
        debug(self.create_db(switch, CREATE_OVSDB_CMD))
        debug(self.remove_db(switch, CONFIGDB))
        debug(self.create_db(switch, CREATE_CONFIGDB_CMD))

    def chk_cur_next_cfg(self, switch):
        table_out = switch.cmd(GET_OPEN_VSWITCH_TABLE_CMD)
        table_out += switch.cmd("echo")
        mylines = table_out.splitlines()

        found_cur = False
        found_next = False
        for x in mylines:
            pair = x.split(':')
            if "cur_cfg" in pair[0]:
                print pair[1]
                if int(pair[1]) > 0:
                    found_cur = True
            elif "next_cfg" in pair[0]:
                if int(pair[1]) > 0:
                    found_next = True

        return found_cur and found_next

    def restart_system(self, switch, option):
        # Stop all daemons
        self.stop_daemon(switch, ALL_DAEMONS)

        # stop any manually started ovsdb-server
        debug(switch.cmd(OVSDB_STOP_CMD))

        # remove and recreate the dbs
        self.rebuild_dbs(switch)

        # start ovsdb-server with or without configdb
        if (option == "noconfig"):
            debug(switch.cmd(OVSDB_STARTUP_CMD_NO_CONFIGDB))
        else:
            debug(switch.cmd(OVSDB_STARTUP_CMD_NORMAL))
        time.sleep(0.2)

        # start the platform daemons
        self.start_daemon(switch, PLATFORM_DAEMONS)
        time.sleep(0.1)

    def test_001_connect_to_db(self, switch):
        info("test_001_connect_to_db.\n")
        info("Verify correctly detects no configdb\n")

        self.restart_system(switch, "noconfig")

        # start cfgd
        out = switch.cmd(CFGD_CMD)
        debug(out)
        if CFG_TBL_NOT_FOUND_MSG in out:
            info("Correct msg received when no configdb.\n")
        else:
            error("Incorrect response when configdb missing.\n")
            info(out+'\n')
            return False

        return True

    def test_002_connect_to_db(self, switch):
        info("test_002_connect_to_db.\n")

        info("Verify connects to configdb\n")

        self.restart_system(switch, "normal")

        # start cfgd
        out = switch.cmd(CFGD_CMD)
        debug(out)

        if CFG_TBL_NOT_FOUND_MSG in out:
            info("Correct msg received when no rows in config table.\n")
        else:
            error("Incorrect response when no rows in config table.\n")
            info(out+'\n')
            return False

        return True

    def test_003_find_startup(self, switch):
        info("test_003_find_startup\n")

        info("Verify finds type == startup row\n")

        self.restart_system(switch, "normal")

        # Add two rows to configdb, one type==startup, one type==testtype
        with open(ADD_STARTUP_ROW_FILE) as f_startup:
            startup_row = f_startup.read()
        with open(ADD_TEST_ROW_FILE) as f_test:
            test_row = f_test.read()

        # Note: I have to use the extra "echo" command to flush out
        #       the buffer, and in some cases, such as the CFGD_CMD,
        #       I need a sleep.
        debug(switch.cmd(startup_row))
        debug(switch.cmd("echo"))
        debug(switch.cmd(test_row))
        debug(switch.cmd("echo"))

        # start cfgd
        out = switch.cmd(CFGD_CMD)
        #HALON_TODO: Need to replace the sleep with a workable solution
        #            in the test infrastructure.
        sleep(5)
        out += switch.cmd("echo")
        debug(out)

        if CFG_DATA_FOUND_MSG in out:
            info("Correct msg received when startup config in config table.\n")
        else:
            error("Incorrect response when startup config in config table.\n")
            info(out+'\n')
            return False

        return True

    def test_004_mark_completion(self, switch):
        info("test_004_mark_completion\n")

        info("Verify cur_cfg and next_cfg set > 0\n")

        # Init everything, but don't really need a config
        self.restart_system(switch, "normal")

        # Run cfgd
        out = switch.cmd(CFGD_CMD)
        sleep(5)
        out += switch.cmd("echo")
        debug(out)

        # Get the contents of the Open_vSwitch table
        if not self.chk_cur_next_cfg(switch):
            info("cur/next cfg not properly set")
            return False
        else:
            info("cur_cfg, next_cfg properly set")

        return True

    def test(self):
        s1 = self.net.switches[0]
        #h1 = self.net.hosts[0]

        # Call the tests.
        ret_status = True

        ret_status &= self.test_001_connect_to_db(s1)
        ret_status &= self.test_002_connect_to_db(s1)
        ret_status &= self.test_003_find_startup(s1)
        ret_status &= self.test_004_mark_completion(s1)

        # True iff all tests returned True
        return ret_status

if __name__ == '__main__':
    test = cfgdTest()
    test.run(runCLI=False)

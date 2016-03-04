# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from time import sleep

TOPOLOGY = """
#
# +-------+
# |  sw1  |
# +-------+
#

# Nodes
[type=openswitch name="Switch 1"] sw1
"""


def start_daemon(switch, daemon):
    switch("/bin/systemctl start " + daemon, shell='bash')
    switch(' ', shell='bash')


def stop_daemon(switch, daemon):
    switch("/bin/systemctl stop " + daemon, shell='bash')
    switch(' ', shell='bash')


def status_daemon(switch, daemon):
    out = switch("/bin/systemctl status " + daemon + " -l", shell='bash')
    switch(' ', shell='bash')
    return out


def remove_db(switch, db):
    switch("/bin/rm -f " + db, shell='bash')


def create_db(switch, db):
    switch(db, shell='bash')


def rebuild_dbs(switch):
    ovsdb = "/var/run/openvswitch/ovsdb.db"
    create_ovsdb_cmd = "/usr/bin/ovsdb-tool create "\
                       "/var/run/openvswitch/ovsdb.db"\
                       " /usr/share/openvswitch/vswitch.ovsschema"
    create_configdb_cmd = "/usr/bin/ovsdb-tool create /var/local/openvswitch/"\
                          "config.db /usr/share/openvswitch/configdb.ovsschema"

    remove_db(switch, ovsdb)
    create_db(switch, create_ovsdb_cmd)
    create_db(switch, create_configdb_cmd)


def restart_system(switch, option):
    all_daemons = "ops-sysd ops-pmd ops-tempd ops-powerd ops-ledd ops-fand"\
                  " switchd ops-intfd ops-vland ops-lacpd"\
                  " ops-lldpd ops-zebra ops-bgpd ovsdb-server"
    ovsdb_stop_cmd = "kill -9 "\
                     "`cat /var/run/openvswitch/ovsdb-server.pid`"
    ovsdb_startup_cmd_no_configdb = "/usr/sbin/ovsdb-server "\
                                    "--remote=punix:/var/"\
                                    "run/openvswitch/db.sock "\
                                    "--detach --no-chdir"\
                                    " --pidfile -vSYSLOG:INFO "\
                                    "/var/run/openvswitch/ovsdb.db"
    ovsdb_startup_cmd_normal = "/usr/sbin/ovsdb-server "\
                               "--remote=punix:/var/run/"\
                               "openvswitch/db.sock "\
                               "--detach --no-chdir --pidfile"\
                               " -vSYSLOG:INFO /var/run/openvswitch/ovsdb.db "\
                               "/var/local/openvswitch/config.db"
    platform_daemons = "ops-sysd ops-pmd ops-tempd "\
                       "ops-powerd ops-ledd ops-fand"

    # Stop all daemons
    stop_daemon(switch, all_daemons)

    # stop any manually started ovsdb-server
    switch(ovsdb_stop_cmd, shell='bash')

    # remove and recreate the dbs
    rebuild_dbs(switch)

    # start ovsdb-server with or without configdb
    if (option == "noconfig"):
        switch(ovsdb_startup_cmd_no_configdb, shell='bash')
    else:
        switch(ovsdb_startup_cmd_normal, shell='bash')
    sleep(0.2)

    # start the platform daemons
    start_daemon(switch, platform_daemons)
    sleep(0.1)


def test_cfgd(topology, step):
    sw1 = topology.get('sw1')

    assert sw1 is not None

    step('### Test to copying startup to running config on bootup ###')
    # Change hostname as CT-TEST in running db and copy the running
    # configuration to startup config. Now restart the system and
    # verify that the hostname is configured correctly during bootup

    sw1('configure terminal')
    sw1('hostname CT-TEST')
    # sw1._shells['vtysh']._prompt = (
    #     '(^|\n)CT-TEST(\\([\\-a-zA-Z0-9]*\\))?#'
    # )
    sw1(' ')
    sw1('end')
    sw1('copy running-config startup-config')
    sleep(5)
    sw1('show running-config')
    sw1('show startup-config')

    restart_system(sw1, "normal")
    sleep(10)

    # Run ops_cfgd
    start_daemon(sw1, "cfgd")
    sleep(10)

    status_daemon(sw1, "cfgd")

    output = sw1('show running-config')

    assert "hostname CT-TEST" in output

    step('### Test to verify cur_cfg and next_cfg set > 0 ###')
    # Init everything, but don't really need a config
    restart_system(sw1, "normal")

    # Run ops_cfgd
    start_daemon(sw1, "cfgd")
    sleep(10)

    status_daemon(sw1, "cfgd")

    # Get the contents of the System table
    table_out = sw1("ovs-vsctl list system", shell='bash')

    assert "cur_cfg" in table_out and "next_cfg" in table_out

    step('### Test to verify correctly ops_cfgd detects no configdb ###')
    restart_system(sw1, "noconfig")

    # start ops_cfgd
    start_daemon(sw1, "cfgd")
    sleep(10)

    out = status_daemon(sw1, "cfgd")

    assert "No rows found in the config table" in out

    step('### Test to verify connects to configdb '
         'and detect no startup row ###')
    # Remove config db file and restart system
    remove_db(sw1, "/var/local/openvswitch/config.db")

    restart_system(sw1, "normal")

    # start ops_cfgd
    start_daemon(sw1, "cfgd")
    sleep(10)

    out = status_daemon(sw1, "cfgd")

    assert "No rows found in the config table" in out

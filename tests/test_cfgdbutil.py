"""
Copyright (C) 2015 Hewlett Packard Enterprise Development LP
All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

#!/usr/bin/python

import os
import sys
import time
import pytest
import subprocess
import json
from halonvsi.docker import *
from halonvsi.halon import *

ADD_STARTUP_ROW_FILE = "./src/ops-cfgd/tests/add_startup_row"
JSON_CONFIG_STRING = "{\"config-type\":\"test\"}"

class cfgdbUtilTests( HalonTest ):

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
      link=HalonLink, controller=None,
      build=True)

  def insert_startup_config(self):
    #configuring Halon, in the future it would be through
    #proper Halon commands
    s1 = self.net.switches[ 0 ]

    #Add one rows to configdb of type==startup
    with open(ADD_STARTUP_ROW_FILE) as f_startup:
        startup_row = f_startup.read()

    output = s1.cmd(startup_row)

  def cfgdbutils_delete_command(self):
    info('\n########## Test cfgdbutils delete commands ##########')
    #configuring Halon, in the future it would be through
    #proper Halon commands
    s1 = self.net.switches[ 0 ]

    info('\n### Delete startup config saved in configdb ###')

    # Note: I have to use the extra "echo" command to flush out
    #       the buffer
    output = s1.cmd("cfgdbutil delete startup-config")
    output += s1.cmd("echo")
    debug(output)

    if 'success' in output:
      info('\n### Passed: Delete startup configuration ###')
    else:
      assert ('success' in out), \
            "Failed: Delete startup configuration"

  def cfgdbutils_show_command(self):
    info('\n########## Test cfgdbutils show commands ##########')

    self.insert_startup_config()
    #configuring Halon, in the future it would be through
    #proper Halon commands
    s1 = self.net.switches[ 0 ]

    # Note: I have to use the extra "end" CLI command to flush out
    #       the buffer.
    output = s1.cmdCLI("show startup-config")
    output += s1.cmdCLI("end")
    debug(output)

    output = output[output.index('{'):]
    output = output[:output.rindex('}') + 1 ]

    parsed =json.loads(output)
    output = json.dumps(parsed, indent=4, sort_keys=True)

    parsed =json.loads(JSON_CONFIG_STRING)
    config_string = json.dumps(parsed, indent=4, sort_keys=True)

    if config_string in output:
      info('\n### Passed: Fetch startup configuration success ###')
    else:
      assert (config_string in out), \
           "Failed: To fetch startup configuration"

  def cfgdbutils_copy_running_startup(self):
    info('\n########## Test copy running to startup config ##########')

    s1 = self.net.switches[ 0 ]

    # Change hostname as CT-TEST in running db and copy the running
    # configuration to startup config and verify the JSON  dump
    # of config contain hostname as CT-TEST("hostname": "CT-TEST").

    s1.cmdCLI("configure terminal")
    s1.cmdCLI("hostname CT-TEST")
    s1.cmdCLI("exit")
    s1.cmdCLI("copy running-config startup-config")

    output = s1.cmdCLI("show startup-config")
    output += s1.cmdCLI("end")

    output = output[output.index('{'):]
    output = output[:output.rindex('}') + 1 ]

    parsed =json.loads(output)
    openvswitch = parsed["Open_vSwitch"]
    for key, value in openvswitch.iteritems():
      hostname = value['hostname']
      break

    if "CT-TEST" in hostname:
      info('\n### Passed: copy running to startup configuration ###')
    else:
      assert ("CT-TEST" in hostname), \
           "Failed: copy running to startup configuration"

  def cfgdbutils_copy_startup_running(self):
    info('\n########## Test copy startup to running config ##########')

    s1 = self.net.switches[ 0 ]

    # Change hostname as openswitch in running db and copy the startup
    # configuration to running config and verify in show running config
    # that hostname is again changed to CT-TEST.
    s1.cmdCLI("configure terminal")
    s1.cmdCLI("hostname openswitch")
    s1.cmdCLI("exit")
    s1.cmdCLI("copy startup-config  running-config")

    output = s1.cmdCLI("show running-config")
    output += s1.cmdCLI("end")

    if "hostname \"CT-TEST\"" in output:
      info('\n### Passed: copy running to startup configuration ###\n')
    else:
      assert ("hostname CT-TEST" in output), \
           "Failed: copy running to startup configuration"

class Test_cfgdbutil:
  def setup(self):
    pass

  def teardown(self):
    pass

  def setup_class(cls):
    Test_cfgdbutil.test = cfgdbUtilTests()
    pass

  def teardown_class(cls):
    # Stop the Docker containers, and
    # mininet topology
    Test_cfgdbutil.test.net.stop()

  def setup_method(self, method):
    pass

  def teardown_method(self, method):
    pass

  def __del__(self):
    del self.test

  # Show command tests.
  def test_show_config_commands(self):
    self.test.cfgdbutils_show_command()

  # Delete command tests.
  def test_delete_config_commands(self):
      self.test.cfgdbutils_delete_command()

  # Copy running to startup config tests.
  def test_cfgdbutils_copy_running_startup(self):
      self.test.cfgdbutils_copy_running_startup()

  # Copy startup to  running config tests.
  def test_cfgdbutils_copy_startup_running(self):
      self.test.cfgdbutils_copy_startup_running()

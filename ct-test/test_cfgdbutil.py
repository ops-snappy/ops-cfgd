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

ADD_STARTUP_ROW_FILE = "add_startup_row"
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
    print('\n=========================================')
    print('*** Test to cfgdbutils delete commands ***')
    print('=========================================')
    #configuring Halon, in the future it would be through
    #proper Halon commands
    s1 = self.net.switches[ 0 ]

    print('Delete startup config saved in configdb')

    # Note: I have to use the extra "echo" command to flush out
    #       the buffer
    output = s1.cmd("cfgdbutil delete startup-config")
    output += s1.cmd("echo")
    debug(output)

    if 'success' in output:
      print(output)
    else:
      print(output)
      assert 0, output

    print('=============================================')
    print('*** End of delete commands ***')
    print('=============================================')

  def cfgdbutils_show_command(self):
    print('\n=========================================')
    print('*** Test to cfgdbutils show commands ***')
    print('=========================================')

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
    output = output[:output.index('}') + 1 ]

    parsed =json.loads(output)
    output = json.dumps(parsed, indent=4, sort_keys=True)

    parsed =json.loads(JSON_CONFIG_STRING)
    config_string = json.dumps(parsed, indent=4, sort_keys=True)

    if config_string in output:
      print("Fetch startup configuration success")
    else:
      print(config_string)
      print(output)
      assert 0, output

    print('=============================================')
    print('*** End of show commands ***')
    print('=============================================')


class Test_cfgdbutil:
#if __name__ == '__main__':
  # Create the Mininet topology based on mininet.
  test = cfgdbUtilTests()

  def setup(self):
    pass

  def teardown(self):
    pass

  def setup_class(cls):
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

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
from cfgmgr import CfgMgr
import subprocess
import json
import unittest

'''
The functions setUp() and tearDown() are called before and after each test_*
fucntion. Since I want to control what is started uniquely for each test, these
two functions are NULL.

Each test_* function is called by unittest in alphabetical order. To properly sequence the test execution I have added numbers to each test (test_XXX).

test_000_startup() is called first and sets up the basic environment.
test_999_shutdown() is called last and shuts everything down.
'''

BASE_DIR = '/tmp/'
CONFIG_DIR = '/var/local/config/'

DEF_CONFIG = 'cfg_def.json'
CONFIG_NAME = 'halon.cfg'
CONFIG_PATH = CONFIG_DIR+CONFIG_NAME

global mgr

class TestCfgd(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run_script(self, name):
        rc = subprocess.call([BASE_DIR+name])
        self.assertEqual(rc,0)

    def read_config(self):
        global mgr
        try:
            cfg_data = mgr.get_config_data()
        except Exception as e:
            print('unable to read configuration from the DAL, e={0}'.format(e))
            cfg_data = None

        self.assertNotEqual(cfg_data, None)
        self.purge_generation(cfg_data)

        return cfg_data

    def purge_generation(self, obj, bad='#generation'):
        if isinstance(obj, dict):
            for k in obj.keys():
                if k == bad:
                    del obj[k]
                else:
                    self.purge_generation(obj[k], bad)
        elif isinstance(obj, list):
            for i in reversed(range(len(obj))):
                if obj[i] == bad:
                    del obj[i]
                else:
                    self.purge_generation(obj[i], bad)
        else:
            # neither a dict nor a list, do nothing
            pass

    def copy_config(self):
        # Copy the default config to the config dir
        rc = subprocess.call(['/bin/mkdir', '-p', CONFIG_DIR])
        rc = subprocess.call(['/bin/cp', '-f', BASE_DIR+DEF_CONFIG,
                        CONFIG_DIR+CONFIG_NAME])
        self.assertEqual(rc,0)

        # Verify copy worked.
        self.assertEqual(os.path.isfile(CONFIG_PATH), True)

    def del_config(self):
        # Delete config file in the config dir
        rc = subprocess.call(['/bin/rm', '-f', CONFIG_PATH])
        self.assertEqual(rc,0)

        # Verify copy worked.
        self.assertEqual(os.path.isfile(CONFIG_PATH), False)

    def load_config(self, name):
        with open(name, 'r') as f:
            data = json.load(f)
        return data

    def compare_obj(self, obj1, obj2):
        if obj1 != obj2:
            print('obj1 is\n{0}\n'.format(json.dumps(obj1, sort_keys=True,
                                  indent=4)))
            print('\nobj2 is\n{0}\n'.format(json.dumps(obj2, sort_keys=True,
                                  indent=4)))
            return False
        else:
            return True

    def disable_remote_load(self):
        #HALON_TODO: Need way to disable remote config load
        #...for now, signal not working
        return False

    def stop_start(self):
        self.run_script('shutdown.sh')
        self.run_script('startup.sh')

    def test_000_startup(self):
        global mgr

        self.stop_start()
        mgr = CfgMgr()

    def test_001_no_cfg_pushed_to_dal(self):
        print 'Running test_001_no_cfg_pushed_to_dal()'

        #HALON_TODO: Need way to disable remote config load
        if self.disable_remote_load() == False:
            print('HALON_TODO: test_001_no_cfg_pushed_to_dal() is DISABLED')
            return

        # Delete the config file
        self.del_config()

        # Start cfgd
        self.stop_start()
        self.run_script('start_cfgd.sh')

        # Read the configuration from the DAL
        cfg = self.read_config()

        # Get the expected config
        expected = self.load_config(BASE_DIR+'cfg_empty.json')

        # Compare what we read against what is expected
        self.assertEqual(self.compare_obj(cfg,expected),True)

    def test_002_local_cfg_pushed_to_dal(self):
        print('Running test_002_local_cfg_pushed_to_dal()')

        # Copy the default config to the config dir
        self.copy_config()

        # Start cfgd
        self.run_script('start_cfgd.sh')

        # Read the configuration from the DAL
        cfg = self.read_config()

        # Get the expected config
        expected = self.load_config(CONFIG_PATH)

        # Compare what we read against what is expected
        self.assertEqual(self.compare_obj(cfg,expected),True)

    def test_003_remote_cfg_pushed_to_dal(self):
        print('Running test_003_remote_cfg_pushed_to_dal()')
        print('HALON_TODO: test_003_remote_cfg_pushed_to_dal() is DISABLED')
        return

        # Delete the config file
        self.del_config()

        # Start cfgd
        self.stop_start()
        self.run_script('start_cfgd.sh')

        # Read the configuration from the DAL
        cfg = self.read_config()

        # Get the expected config
        expected = self.load_config(BASE_DIR+'cfg_empty.json')

        # Compare what we read against what is expected
        self.assertEqual(self.compare_obj(cfg,expected),True)

    def test_999_shutdown(self):
        self.run_script('shutdown.sh')

if __name__ == '__main__':
    unittest.main()

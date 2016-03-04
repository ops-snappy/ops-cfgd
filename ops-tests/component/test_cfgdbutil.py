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

import json

TOPOLOGY = """
#
# +-------+
# |  sw1  |
# +-------+
#

# Nodes
[type=openswitch name="Switch 1"] sw1
"""


def test_cfgdb_util(topology, step):
    sw1 = topology.get('sw1')

    assert sw1 is not None

    step("### Test cfgdbutils show commands ###")
    sw1('configure terminal')
    sw1('lldp holdtime 9')
    sw1('radius-server host 1.1.1.1')
    sw1('end')
    sw1('copy running-config startup-config')
    output = sw1('show startup-config')

    assert "lldp holdtime 9" in output and \
           "radius-server host 1.1.1.1" in output

    step("### Test to show startup config in json ###")
    output = sw1('show startup-config json')
    output = output[output.index('{'):]
    output = output[:output.rindex('}') + 1]

    parsed = json.loads(output)
    system = parsed["System"]
    radius_servers = system["radius_servers"]

    assert "1.1.1.1" in radius_servers

    step("####   Delete startup config saved in configdb   ###")
    output = sw1('cfgdbutil delete startup-config', shell='bash')

    assert "success" in output

    step("### Test copy running to startup config ###")
    sw1('configure terminal')

    sw1('hostname CT-TEST')

    # sw1._shells['vtysh']._prompt = (
    #     '(^|\n)CT-TEST(\\([\\-a-zA-Z0-9]*\\))?#'
    # )
    sw1(' ')

    sw1('end')
    sw1('copy running-config startup-config')
    output = sw1('show startup-config')

    assert "CT-TEST" in output

    step('### Test copy startup to running config ###')
    sw1('configure terminal')
    sw1('hostname openswitch')
    # sw1._shells['vtysh']._prompt = (
    #     '(^|\n)openswitch(\\([\\-a-zA-Z0-9]*\\))?#'
    # )
    sw1(' ')
    sw1('end')
    sw1('copy startup-config running-config')
    output = sw1('show running-config')
    assert "hostname CT-TEST" in output

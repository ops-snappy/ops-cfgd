#!/bin/sh
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

if [ "x" = "${TARGET_IP}x" ]; then
    echo "Test target IP address not specified"
    exit 1
fi

# Files to be copied to target.
TEST_DRIVER=cfgd_test.py
COPY_FILES=./remotefiles/*

# Copy test programs to target
# HALON_TODO: The test setup code should make sure that the host
#             side ssh tools do not prompt about stale known_hosts
#             entries.
scp ${TEST_DRIVER} ${COPY_FILES} root@${TARGET_IP}:/tmp/
RC=$?
if [ 0 -ne ${RC} ]; then
    echo "Failed copy test programs to target ${TARGET_IP}"
    exit 2
fi

EC=0

# Run the remote tests.
ssh root@${TARGET_IP} python /tmp/${TEST_DRIVER}

RC=$?
if [ 0 -ne ${RC} ]; then
    echo "Failed run test programs on target @ ${TARGET_IP}"
    ssh root@${TARGET_IP} /bin/rm -f /tmp/${COPY_FILES}
    EC=3
fi

# Clean up test binaries on target.
ssh root@${TARGET_IP} /bin/rm -f /tmp/${COPY_FILES} /tmp/${TEST_DRIVER}
RC=$?
if [ 0 -ne ${RC} ]; then
    echo "Failed to cleanup test programs on target @ ${TARGET_IP}"
    EC=4
fi

exit ${EC}

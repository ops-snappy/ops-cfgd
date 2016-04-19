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

import os
import sys

import ovs.dirs
from ovs.db import error
from ovs.db import types
import ovs.db.idl
import ovs.vlog
import ovs.poller

vlog = ovs.vlog.Vlog("cfgdb")

# ovs definitions
idl = None
# OPS_TODO: Need to pull this from the build env
def_db = 'unix:/var/run/openvswitch/db.sock'

# OPS_TODO: Need to pull this from the build env
cfgdb_schema = '/usr/share/openvswitch/configdb.ovsschema'

#Configdb tabe names
CONFIG_TABLE = "config"

#configdb column names
CONFIG = "config"
TYPE = "type"
NAME = "name"
WRITER = "writer"
DATE = "date"
HARDWARE = "hardware"


class Cfgdb(object):
    def __init__(self, location=None):
        '''
        Creates a Idl connection to the configdb and register all the columns
        with schema helper.

        Maintain the self global value for all the columns in configdb that
        can be modified and updated to existing row or inserted as new row.
        '''
        self.idl = None
        self.txn = None
        self.schema_helper = ovs.db.idl.SchemaHelper(location=cfgdb_schema)
        self.schema_helper.register_columns(CONFIG_TABLE,
                                            [TYPE, NAME, WRITER,
                                             DATE, CONFIG, HARDWARE])

        self.idl = ovs.db.idl.Idl(def_db, self.schema_helper)

        self.config = None
        self.type = "startup"
        self.name = None
        self.writer = None
        self.date = None
        self.hardware = None

        curr_seqno = self.idl.change_seqno
        while True:
            self.idl.run()
            if curr_seqno != self.idl.change_seqno:
                break
            poller = ovs.poller.Poller()
            self.idl.wait(poller)
            poller.block()

    def find_row_by_type(self, cfgtype):
        '''
        Walk through the rows in the config table (if any)
        looking for a row with type parsed in argument

        If row found set variable tbl_found to True and return
        the row object to caller function
        '''
        tbl_found = False
        ovs_rec = None
        for ovs_rec in self.idl.tables[CONFIG_TABLE].rows.itervalues():
            if ovs_rec.type == cfgtype:
                tbl_found = True
                break

        return ovs_rec, tbl_found

    def __set_column_value(self, row):
        status = "Invalid"

        if self.config is not None:
            setattr(row, CONFIG, self.config)

        #Currently only "startup" type is supported
        if self.type is not "startup":
            return status
        else:
            setattr(row, TYPE, self.type)
            status = "success"

        if self.name is not None:
            setattr(row, NAME, self.name)

        if self.writer is not None:
            setattr(row, WRITER, self.writer)

        if self.date is not None:
            setattr(row, DATE, self.date)

        if self.hardware is not None:
            setattr(row, HARDWARE, self.hardware)

        return status

    def insert_row(self):
        '''
        Insert a new row in configdb and update the columns with
        user values (default values are taken if columns values
        not given by user) in global variables.
        '''
        self.txn = ovs.db.idl.Transaction(self.idl)
        row = self.txn.insert(self.idl.tables[CONFIG_TABLE])

        status = self.__set_column_value(row)

        if (status is not "success"):
            return None, status
        else:
            status = self.txn.commit_block()

        return row, status

    def update_row(self, row):
        '''
        Update the row with the latest modified values.
        '''
        self.txn = ovs.db.idl.Transaction(self.idl)

        status = self.__set_column_value(row)

        if (status is not "success"):
            return None, status
        else:
            status = self.txn.commit_block()

        return row, status

    '''
    OPS_TODO: This probably should be by TYPE and NAME. In
    the future we could possibly have multiple row of same
    type with different names. However, currently we support
    only one row and "startup" is supposed to be a "one only"
    type so there is no ambiguity of which is the startup config.
    '''
    def delete_row_by_type(self, cfgtype):
        '''
        Delete a specific row from configdb based on
        config type passed as argument

        If specified row is found, variable row_found
        is updated to True and delete status is returned
        '''
        self.txn = ovs.db.idl.Transaction(self.idl)
        row, row_found = self.find_row_by_type(cfgtype)
        status = "unchanged"

        if row_found:
            row.delete()
            status = self.txn.commit_block()

        return status, row_found

    def close(self):
        self.idl.close()

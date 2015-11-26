# High level design of ops-cfgd

## Table of Contents
- [cfgd daemon](#cfgd-daemon)
- [cfgdbutils](#cfgdbutils)

## CFGD Daemon
### Feature description
The cfgd daemon process is started by systemd when the switch boots up. The cfgd daemon is responsible for updating the persistent startup configuration to the OVSDB database and notifying all other daemons waiting for configuration to be available.

### Responsibilities
The cfgd daemon is responsible for updating the persistent configuration into the OVSDB database and updating the state (cur_cfg) in the OVSDB database.

During initialization, the platform daemons discover all hardware present and populate the OVSDB database with hardware related information.

The cfgd daemon checks for any saved configurations with the type **startup**. If a startup configuration is available, it is applied to all tables in the OVSDB database.

### Design choices
N/A

### Relationships to external OpenSwitch entities
```ditaa
            +---------------------+
            |                     |
            |        CLI          |
            +---------------------+
                        |
                        |
            +-----------v--------------------------------------+
            |        Config persistence utility                |
            |                                                  |
            +--------------------------------------------------+
                        |                               |
                        |                               |
            +-----------v----------------------+        |
            |      REST API                    |        |
            |                                  |        |
            +----------------------------------+        |
                        |                               |
                        |                               |
                        |                               |
            +-----------v----------------------+  +-----v------------------+
            | +----------------+     OVSDB     |  | +---------+            |
            | |   Running      |               |  | |startup  |   Configdb |
            | |   Config       |               |  | |Config   |            |
            | +----------------+               |  | +---------+            |
            +----------------------------------+  +------------------------+
```

The startup configuration is stored in the OVS database file located at "/var/local/openvswitch/config.db".

The running configuration is present in the ovsdb.db file, currently located (on a running system) at "/var/run/openvswitch".

### OVSDB-Schema
N/A

### Internal structure
The cfgd daemon is implemented using the following API library:

Configuration Read/Write API: These APIs perform conversion between the startup configuration in JSON format and the running configuration in OVSDB table format that is described in the vswitchd.extschema.

The cfgd daemon uses the dispatcher design concept to perform its operations. The basic flow is as follows:
1) Creates an idl object and calls idl.run () until idl is in sync with the running config db.
2) dispatcher: This calls the next function in a function table, allowing functionality sequencing. If the function returns True, the function pointer is incremented to call the next function during the next loop. If the function returns False, the function pointer is not incremented and the same function is executed again.

The function table contains the following function in the same order:
- wait_for_hw_done: This function returns a False (after a short sleep) until the open_vswitch:cur_hw is greater than 0. The cfgd should not push the user config until after hardware initialization has been completed by the platform daemons.

- push_cfg_to_db: If the save_config is not None, this function pushes the configuration to the ovsdb.

- mark_completion: Sets the open_vswitch:cur_cfg to > 0. The protocl daemons should not start processing until after the user configuration (if it exists) has been pushed. This value being >0 indicates that the system config (hardware and user config) has been completed.

- terminate: Sets the global variable exiting to True.

## cfgdbutils
###  Feature description
The cfgdbutil is a python utility used to perform operations such as copying the startup configuration to a running configuration, copying a running configuration to the startup configuration, and showing the startup configuration for use by CLI applications.

### Responsibilities
The cfgdbutil is responsible for providing commands for showing, copying, and deleting startup configurations from the configdb.

CLI calls cfgdbutil to perform "show startup-config", "copy startup-config", and "copy running-config startup-config" commands.

### Design choices
N/A

### Relationships to external OpenSwitch entities

```ditaa
            +---------------------+
            |                     |
            |        CLI          |
            +---------------------+
                        |
                        |
            +-----------v--------------------------------------+
            |        Config persistence utility                |
            |                                                  |
            +--------------------------------------------------+
                        |                               |
                        |                               |
            +-----------v----------------------+        |
            |      REST API                    |        |
            |                                  |        |
            +----------------------------------+        |
                        |                               |
                        |                               |
                        |                               |
            +-----------v----------------------+  +-----v------------------+
            | +----------------+     OVSDB     |  | +---------+            |
            | |   Running      |               |  | |startup  |   Configdb |
            | |   Config       |               |  | |Config   |            |
            | +----------------+               |  | +---------+            |
            +----------------------------------+  +------------------------+

```



### Internal structure
The cfgdbutil is implemented using two API libraries:

1. Configuration Read/Write API library: These APIs perform conversion between the startup configuration in JSON format and the running configuration in the form of the OVSDB tables described in vswitchd.extschema

2. cfgdb API library : These APIs perform insert and update startup rows and create idl objects with the configdb config tables described in configdb.ovsschema.



The cfgdbutil uses an argument design concept to perform its operations. The basic flow is as follows:
1) The cfgdbutil takes operations to be performed such as show, copy, and delete as arguments.
2) The cfgdbutil creates an **idl** object and calls idl.run () until **idl** is in sync with the running config db.

### The commands supported by cfgdbutil
#### Show startup-config
This command fetches the startup configuration stored in the configdb in JSON format and shows it in the console.

#### Copy startup-config running-config
This command copies the content of the startup configuration to the current system's running configuration.

#### Copy running-conig startup-config
This command copies the content of the current system's running configuration to the startup configuration.

#### Delete startup-config
This command deletes rows with type=**startup** from the configdb.

## References

For Command Reference document of ops-cfgd, refer to [Config persistence Command Reference](/documents/user/config_persistence_CLI)

# Config persistent component test cases

## Contents##
- [Test cases to verify Config Persistence daemon](#test-cases-to-verify-config-persistence-daemon)
    - [Test to verify no configdb detection](#test-to-verify-no-configdb-detection)
    - [Test to verify configdb detection and connection](#test-to-verify-configdb-detection-and-connection)
    - [Test to verify configdb detect startup row](#test-to-verify-configdb-detect-startup-row)
    - [Test to verify configdb mark completion](#test-to-verify-configdb-mark-completion)
    - [Test to verify startup config push during boot](#test-to-verify-startup-config-push-during-boot)
- [Test cases to verify Config Persistence utility](#test-cases-to-verify-config-persistence-utility)
    - [Test to verify show startup configuration](#test-to-verify-show-startup-configuration)
    - [Test to verify delete startup configuration](#test-to-verify-delete-startup-configuration)
    - [Test to verify running configuration to startup configuration](#test-to-verify-running-configuration-to-startup-configuration)
    - [Test to verify startup configuration to running configuration](#test-to-verify-startup-configuration-to-running-configuration)

##Test cases to verify the config persistence daemon ##
### Objective ###
Test cases to verify that the configdb and the cfgd daemon work.
### Requirements ###
The requirements for this test case are:

 - AS5712 switch

### Setup ###
#### Topology diagram ####
```ditaa
              +------------------+
              |                  |
              |  AS5712 switch   |
              |                  |
              +------------------+
```

### Test to verify no configdb detection  ###
#### Description ####
Test to verify that the config persistence daemon detects that configdb is not present and logs the correct error.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the "No rows found in the config table" error message is received.
#### Test fail criteria ####
Test case result is a fail if the "No rows found in the config table" error message is not received.

### Test to verify configdb detection and connection  ###
#### Description ####
Test to verify that the config persistence daemon detects configdb and connects to db.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the cfgd is able to detect an empty configdb with no row present.
#### Test fail criteria ####
Test case result is a fail if the cfgd is not able connect to the configdb.


### Test to verify configdb detect startup row  ###
#### Description ####
Test to verify that the config persistence daemon detects a startup row in the configdb.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the "Config data found" message is received.
#### Test fail criteria ####
Test case result is a fail if  the "Config data found" message is not received.


### Test to verify configdb mark completion  ###
#### Description ####
Test to verify that the config persistence daemon marks completion in the configdb after pushing a startup config to a running config.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the cur_cfg and next_cfg in the System table is greater than 1.
#### Test fail criteria ####
Test case result is a fail if the cur_cfg and next_cfg in the System table is zero or empty.


### Test to verify startup config push during boot ###
#### Description ####
Test to verify that the config persistence daemon copies the startup config saved in the configdb to the running db during boot up time, then saves a startup config with hostname configured to "CT-TEST" and the system is rebooted.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the hostname in the System table is "CT-TEST"
#### Test fail criteria ####
Test case result is a fail if the hostname in the System table is not "CT-TEST".


## Test cases to verify Config Persistence utility ##
### Objective ###
Test cases to verify that the cfgdbutil performs a copy configuration and shows the configuration correctly.
### Requirements ###
The requirements for this test case are:

 - AS5712 switch

### Setup ###
#### Topology diagram ####
```ditaa
              +------------------+
              |                  |
              |  AS5712 switch   |
              |                  |
              +------------------+
```

#### Test setup ####
### Test to verify show startup configuration  ###
#### Description ####
Test to verify that the config persistence utility fetches the startup configuration in JSON format from the startup row in the configdb. Saves a dummy JSON string in the startup row, executes the show command and then compares the output of the show command and the configured dummy JSON string to verify they are the same.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the show command output matches with the JSON string configured during setup.
#### Test fail criteria ####
Test case result is a fail if the show command output doesn't match with the JSON string configured during setup.

### Test to verify delete startup configuration ###
#### Description ###
Test to verify that the config persistence utility fetches a startup row in the configdb and deletes it. Inserts a dummy row with type = startup and executes the delete command.
### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the show command output matches with the JSON string configured during setup.

#### Test fail criteria ####
Test case result is a fail if the show command output doesn't match with the JSON string configured during setup.

### Test to verify running configuration to startup configuration ###
#### Description ###
Test to verify that the config persistence utility copies the current system running configuration and saves it in JSON format in the startup row of the configdb. Configure hostname as "CT-TEST" in the running configuration and execute a copy running the configuration to startup configuration.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the saved JSON string in the startup row contains hostname key value as "CT-TEST" in the System table.
#### Test fail criteria ####
Test case result is a fail if the saved JSON string in the startup row does not contain the hostname key value as "CT-TEST" in the System table.

### Test to verify startup configuration to running configuration###
#### Description ###
Test to verify that the config persistence utility copies the saved JSON format configuration in the startup row of the configdb to the current system running configuration. Save a startup JSON string in the startup row with the hostname configured to "CT-TEST" and execute a copy of the startup config to the running config.

### Test result criteria ###
#### Test pass criteria ####
Test case result is a success if the `show running-config` command has hostname configured as "CT-TEST".

#### Test fail criteria ####
Test case result is fail if the `show running-config` command has a hostname not configured as "CT-TEST".

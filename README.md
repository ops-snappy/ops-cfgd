# Read me for ops-cfgd repository
# Table of Contents
[toc]

## What is ops-cfgd?

The OVSDB database contains the running configuration of the switch. The ops-cfgd module is responsible for updating the OVSDB database with the startup configuration during system bootup.

## What is the structure of the repository?

* ./ - contains all the source file.
* tests/ - contains all the component tests

## What is the license?
Apache 2.0 license. For more details refer to COPYING

## What other documents are available?

For the high level design of ops-cfgd, refer to [Config persistence design](/documents/dev/ops-cfgd/design)
For Command Reference document of ops-cfgd, refer to [Config persistence Command Reference](/documents/user/config_persistence_CLI)

For general information about OpenSwitch project refer to http://www.openswitch.net

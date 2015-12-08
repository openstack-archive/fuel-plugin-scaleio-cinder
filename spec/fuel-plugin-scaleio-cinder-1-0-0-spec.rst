===========================================================
Fuel plugin for ScaleIO-Cinder clusters as a Cinder backend
===========================================================

ScaleIO-Cinder plugin for Fuel extends Mirantis OpenStack functionality by adding
support for ScaleIO clusters for Cinder backend.

Problem description
===================

Currently, Fuel has no support for ScaleIO clusters as block storage for
OpenStack environments. ScaleIO-Cinder plugin aims to provide support for it.
This plugin will configure OpenStack environments with an existing ScaleIO cluster

Proposed change
===============

Implement a Fuel plugin that will configure the ScaleIO-Cinder driver for
Cinder on all Controller nodes and Compute nodes. All Cinder services run
on controllers no additional Cinder node is required in environment.

Alternatives
------------
None

Data model impact
-----------------

None

REST API impact
---------------

None

Upgrade impact
--------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The ScaleIO-Cinder storage clusters provide high performance block storage for
OpenStack environment, and therefore enabling the ScaleIO-Cinder driver in OpenStack
will greatly improve peformance of OpenStack.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

The plugin generates the approriate cinder.conf to enable the ScaleIO-Cinder
cluster within OpenStack. There are scaleio driver and filter required files, the plugin 
contains the files and will copy them to the correct location.

Cinder-volume service is installed on all Controller nodes and Compute nodes. 
All instances of cinder-volume have the same “host” parameter in cinder.conf
file. This is required to achieve ability to manage all volumes in the
environment by any cinder-volume instance.

Assignee(s)
-----------
| Patrick Butler Monterde <Patrick.ButlerMonterde@emc.com>
| Magdy Salem <magdy.salem@emc.com>
| Adrián Moreno <Adrian.Moreno@emc.com>

Work Items
----------

* Implement the Fuel plugin.
* Implement the Puppet manifests.
* Testing.
* Write the documentation.

Dependencies
============

* Fuel 6.1 and higher.

Testing
=======

* Prepare a test plan.
* Test the plugin by deploying environments with all Fuel deployment modes.

Documentation Impact
====================

* Deployment Guide (how to install the storage backends, how to prepare an
  environment for installation, how to install the plugin, how to deploy an
  OpenStack environment with the plugin).
* User Guide (which features the plugin provides, how to use them in the
  deployed OpenStack environment).
* Test Plan.
* Test Report.


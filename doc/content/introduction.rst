
## Introduction

Fuel plugin for ScaleIO for enabling OpenStack to work with an **External** ScaleIO deployment. This ScaleIO plugin for Fuel extends Mirantis OpenStack functionality by adding support for ScaleIO block storage.

ScaleIO is a software-only solution that uses existing servers' local disks and LAN to create a virtual SAN that has all the benefits of external storage—but at a fraction of cost and complexity. ScaleIO utilizes the existing local internal storage and turns it into internal shared block storage.

The following diagram shows the plugin's high level architecture: 

![ScaleIO Fuel plugin high level architecture](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/fuel-plugin-scaleio-cinder-1.jpg)


From the figure we can see that we need the following OpenStack roles and services: 


Service/Role Name | Description | Installed in |
|------------|-------------|--------------|
|Controller Node + Cinder Host |A node that runs network, volume, API, scheduler, and image services. Each service may be broken out into separate nodes for scalability or availability. In addition this node is a Cinder Host, that contains the Cinder Volume Manager|OpenStack Cluster|
|Compute Node |A node that runs the nova-compute daemon that manages Virtual Machine (VM) instances that provide a wide range of services, such as web applications and analytics.|OpenStack Cluster|


In the **external ScaleIO cluster** we have installed the following roles and services: 

Service Name | Description | Installed in |
|------------|-------------|--------------|
|SclaeIO Gateway (REST API)|The ScaleIO Gateway Service, includes the REST API to communicate storage commands to the SclaeIO Cluster, in addtion this service is used for authentication and certificate management.|ScaleIO Cluster|
|Meta-data Manager (MDM)|Configures and monitors the ScaleIO system. The MDM can be configured in redundant Cluster Mode, with three members on three servers, or in Single Mode on a single server.|ScaleIO Cluster|
|Tie Breaker (TB)|Tie Breaker service helps determining what service runs as a master vs. a slave |ScaleIO Cluster|
|Storage Data Server (SDS)|Manages the capacity of a single server and acts as a back-end for data access.The SDS is installed on all servers contributing storage devices to the ScaleIO system. These devices are accessed through the SDS.|ScaleIO Cluster| 
|Storage Data Client (SDC)|A lightweight device driver that exposes ScaleIO volumes as block devices to the application that resides on the same server on which the SDC is installed.|Openstack Cluster|

**Note:** for more information in how to deploy a ScaleIO Cluster, please refer to the ScaleIO manuals located in the download packages for your platform: [http://www.emc.com/products-solutions/trial-software-download/scaleio.htm](http://www.emc.com/products-solutions/trial-software-download/scaleio.htm "Download ScaleIO") and/or [watch the demo](https://community.emc.com/docs/DOC-45019 "Watch our demo to learn how to download, install, and configure ScaleIO")



## Requirements

These are the plugin requirements: 


| Requirement                                              | Version/Comment |
|----------------------------------------------------------|-----------------|
| Mirantis OpenStack compatibility                         | >= 6.1          |
| ScaleIO Version										   | >= 1.32         |
| Controller and Compute Nodes' Operative System		   | CentOS/RHEL 6.5 |
| OpenStack Cluster (Controller/cinder-volume node) can access ScaleIO Cluster | via a TCP/IP Network  |
| OpenStack Cluster (Compute nodes) can access ScaleIO Cluster| via a TCP/IP Network  |
| Install ScaleIO Storage Data Client (SDC) in Controller and Compute Nodes| Plugin takes care of install|


## Limitations

Currently Fuel doesn't support multi-backend storage.


## Configuration


Plugin files and directories:

|File/Directory|Description|
|--------------|-----------|
|Deployment_scripts| Folder that includes the bash/puppet manifests for deploying the services and roles required by the plugin|
|Deployment_scripts/puppet||
|environment_config.yaml|Contains the ScaleIO plugin parameters/fields for the Fuel web UI|
|metadata.yaml|Contains the name, version and compatibility information for the ScaleIO plugin|
|pre_build_hook|Mandatory file - blank for the ScaleIO plugin|
|repositories/centos|Empty Directory, the plugin scripts will download the required CentOS packages|
|repositories/Ubuntu|Empty Directory, not used|
|taks.yaml|Contains the information about what scripts to run and how to run them|


This Fuel plugin will install the ScaleIO Storage Data Client (SDC) service on each Controller node and Compute node in the cluster. This is necessary in order for the VMs in each compute node to utilize ScaleIO Storage:

![Plugin Architecture ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/fuel-plugin-scaleio-cinder-2.jpg)


Before starting a deployment there are some things that you should verify:

1. Your ScaleIO Cluster can route 10G Storage Network to all Compute nodes
   as well as the Cinder Control/Manager node.
2. Create an account on the ScaleIO cluster to use as the OpenStack Administrator
   account (use the login/password for this account as san_login/password settings).
3. Obtain the IP address from the ScaleIO cluster

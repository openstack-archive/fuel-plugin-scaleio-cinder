
### ScaleIO Cinder plugin installation

The first step is to install the ScaleIO Cinder plugin in the Fuel Master:

1. Download the plugin from the [releases section](https://github.com/openstack/fuel-plugin-scaleio-cinder/releases "Releases Page") or from the [Fuel plugins catalog](https://www.mirantis.com/products/openstack-drivers-and-plugins/fuel-plugins/ "Fuel Plugins Catalog").
 
2. Copy the plugin to an already installed Fuel Master node. If you do not have the Fuel Master node yet, follow the instructions from the official Mirantis OpenStack documentation:

     `scp  fuel-plugin-scaleio-cinder-1.0.noarch.rpm root@:<the_Fuel_Master_node_IP>:/tmp`

3. Log into the Fuel Master node and install the plugin, if downloaded in the `/tmp` directory:

	`cd /tmp`
	`fuel plugins --install /tmp/fuel-plugin-scaleio-cinder-1.0.noarch.rpm`
    

4. Verify that the plugin has been installed successfully: 

![Plugin Installation](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-1.png)



### ScaleIO Cinder plugin configuration

Once the plugin has been installed in the Master, we configure the nodes and set the parameters for the plugin:


1. Start by creating a new OpenStack environment following the [Mirantis instructions](https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#create-a-new-openstack-environment "Creating a new OpenStack environment") 

2. Configure your environment following the [Mirantis OpenStack configuration documentation](https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#configure-your-environment)

	![OpenStack Node configuration](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-2.png)

3. Open the **Settings tab** of the Fuel web UI and scroll down the page. Select the Fuel plugin check-box to enable ScaleIO Cinder plugin for Fuel:

	![ScaleIO Cluster Parameters](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-4.PNG)
	
	**Plugin's parameters explanation:** 
	
	|Parameter Name       |Parameter Description|
	|---------------------|---------------------|
	|ScaleIO Repo URL| The URL of the ScaleIO sources repository. This is the URL for the required scaleIO zip file that contains the ScaleIO product. **The URL can point to an external repository (requires external network access to that repository) or to an internal server in the local network (a local webserver)**. For our example we are using the URI for the [ScaleIO Linux download](http://downloads.emc.com/emc-com/usa/ScaleIO/ScaleIO_Linux_SW_Download.zip "ScaleIO Linux Download") located in the ScaleIO trial download at [EMC.com](http://www.emc.com/products-solutions/trial-software-download/scaleio.htm "ScaleIO Trial Download"). |
	|userName|The ScaleIO User Name|
	|Password|The SclaeIO password for the selected user name|
	|ScaleIO GW IP|The IP address of the the ScaleIO Gateway service|
	|ScaleIO Primary IP|The ScaleIO cluster's primary IP address|
	|ScaleIO Secondary IP|The ScaleIO cluster's secondary IP address|
	|ScaleIO protection domain|Name of the ScaleIO's protection domain|
	|ScaleIO storage pool 1|Name of the first storage pool|
	|Fault sets list|List of the fault sets (comma separated)|
	
	**Note:** Please refer to the ScaleIO documentation for more information on these parameters 

	This is an example of the ScaleIO configuration paremets populated: 

	![ScaleIO Cluster Parameters](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-5.PNG)


4. After the configuration is done, you can Add the nodes to the Openstack Deployment. There is a minimum of two nodes for this configuration: 

	Service/Role Name | Description |
	|------------|-------------|
	|Controller Node + Cinder Host |A node that runs network, volume, API, scheduler, and image services. Each service may be broken out into separate nodes for scalability or availability. In addition this node is a Cinder Host, that contains the Cinder Volume Manager|
	|Compute Node |A node that runs the nova-compute daemon that manages Virtual Machines (VMs) instances that provide a wide range of services, such as web applications and analytics.|

	![OpenStack Node Deployment](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-3.PNG)

	**Note:** you can run the [network verification](https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#verify-networks) check and [deploy the environment](https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#deploy-changes). 

	After this is complete you should see a success message:

	![OpenStack Deployment Successful](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-complete.jpg)

	**Note:** It make take an hour or more for the OpenStack deployment to complete, depending on your hardware configuration. 


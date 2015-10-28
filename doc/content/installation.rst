Install ScaleIO Cinder Plugin
=============================

To install the MidoNet Fuel plugin:

#. Download it from the `Fuel Plugins Catalog`_
#. Copy the *rpm* file to the Fuel Master node:
   ::

      [root@home ~]# scp scaleio-cinder-1.0-1.0.0-1.noarch.rpm root@fuel:/tmp

#. Log into Fuel Master node and install the plugin using the
   `Fuel CLI <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#using-fuel-cli>`_:

   ::

      [root@fuel ~]# fuel plugins --install scaleio-cinder-1.0-1.0.0-1.noarch.rpm

#. Verify that the plugin is installed correctly:
   ::

     [root@fuel-master ~]# fuel plugins
     id | name    | version | package_version
     ---|---------|---------|----------------
     1  | scaleio-cinder | 1.0.0   | 1.0.0

===========================================================
ScaleIO Cinder plugin configuration
===========================================================
Once the plugin has been installed in the Master, we configure the nodes and set the parameters for the plugin:


1. Start by creating a new OpenStack environment following the https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#create-a-new-openstack-environment "Creating a new OpenStack environment") 

2. Configure your environment following the https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#configure-your-environment

	.. image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-2.png

3. Open the **Settings tab** of the Fuel web UI and scroll down the page. Select the Fuel plugin check-box to enable ScaleIO Cinder plugin for Fuel:

	.. image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-4.PNG
	
	**Plugin's parameters explanation:** 
	
	+-------------------------+---------------------------------------------------------+
	|Parameter Name           |Parameter Description				    |
	+=========================+=========================================================+
	|userName                 |The ScaleIO User Name				    |
	+-------------------------+---------------------------------------------------------+
	|Password                 |The SclaeIO password for the selected user name	    |
	+-------------------------+---------------------------------------------------------+
	|ScaleIO GW IP            |The IP address of the the ScaleIO Gateway service	    |
	+-------------------------+---------------------------------------------------------+
	|ScaleIO Primary IP       |The ScaleIO cluster's primary IP address		    |
	+-------------------------+---------------------------------------------------------+
	|ScaleIO Secondary IP     |The ScaleIO cluster's secondary IP address		    |
	+-------------------------+---------------------------------------------------------+
	|ScaleIO protection domain|Name of the ScaleIO's protection domain		    |
	+-------------------------+---------------------------------------------------------+
	|ScaleIO storage pool 1   |Name of the first storage pool			    |
	+-------------------------+---------------------------------------------------------+
	
	**Note:** Please refer to the ScaleIO documentation for more information on these parameters 

	This is an example of the ScaleIO configuration paremets populated: 

	.. image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-5.PNG

4. After the configuration is done, you can Add the nodes to the Openstack Deployment. 
	.. image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-3.PNG

**Note:** you can run the 
check and https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#deploy-changes. 

After this is complete you should see a success message:
	.. image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-complete.jpg

**Note:** It make take an hour or more for the OpenStack deployment to complete, depending on your hardware configuration. 


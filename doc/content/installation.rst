Install ScaleIO Cinder Plugin
=============================

To install the ScaleIO-Cinder Fuel plugin:

#. Download it from the `Fuel Plugins Catalog <https://www.mirantis.com/products/openstack-drivers-and-plugins/fuel-plugins/>`_
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
     1  | scaleio-cinder| 1.0.0   | 1.0.0

===========================================================
ScaleIO Cinder plugin configuration
===========================================================
Once the plugin has been installed in the Master, we configure the nodes and set the parameters for the plugin:


#. Start by creating a new OpenStack environment following the
   `Mirantis OpenStack User Guide <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#create-a-new-openstack-environment>`_.

#. `Configure your environment <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#configure-your-environment>`_.

	.. image:: doc/images/scaleio-cinder-install-2.png

#. Open the **Settings tab** of the Fuel web UI and scroll down the page.
   Select the Fuel plugin checkbox to enable ScaleIO Cinder plugin for Fuel:

	.. image:: doc/images/scaleio-cinder-install-4.PNG

   +----------------------------+----------------------------------------------------+
   |   Parameter name           |         Parameter description                      |
   |                            |                                                    |
   +============================+====================================================+
   | userName                   |   The ScaleIO User name                            |
   +----------------------------+----------------------------------------------------+
   | Password                   | The ScaleIO password for the selected user name    |
   +----------------------------+----------------------------------------------------+
   | ScaleIO GW IP              | The IP address of the the ScaleIO Gateway service  |
   +----------------------------+----------------------------------------------------+
   | ScaleIO Primary IP         |   The ScaleIO cluster's primary IP address         |
   +----------------------------+----------------------------------------------------+
   | ScaleIO Secondary IP       |  The ScaleIO cluster's secondary IP address        |
   +----------------------------+----------------------------------------------------+
   | ScaleIO protection domain  |   Name of the ScaleIO's protection domain          |
   +----------------------------+----------------------------------------------------+
   | ScaleIO storage pool 1     |   Name of the first storage pool                   |
   +----------------------------+----------------------------------------------------+
	
	**Note:** Please refer to the ScaleIO documentation for more information on these parameters 

	This is an example of the ScaleIO configuration paremets populated: 

	.. image:: doc/images/scaleio-cinder-install-5.PNG

4. After the configuration is done, you can Add the nodes to the Openstack Deployment.

	.. image:: doc/images/scaleio-cinder-install-3.PNG

**Note:** you can run the 
check and `deploy changes <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#deploy-changes>`_ then.

After this is complete you should see a success message:

	.. image:: doc/images/scaleio-cinder-install-complete.jpg

**Note:** It make take an hour or more for the OpenStack deployment to complete, depending on your hardware configuration. 


===========================================================
User Guide
===========================================================
1.	Upload scaleio-cinder plugin code to the master node 
 ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image001.png)
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image002.png)  Build the code using fpb –build command
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image003.png)

2.	Install scaleio-cinder plugin using fuel plugins –install command
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image004.png)

3.	Ensure that plugin is installed successfully using cli
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image005.png)
4.	Create environment with enabled plugin in fuel ui, lunch the fuel site and check setting section to make sure the Scaleio-Cinder section exists

5.	Add 3 nodes with Controller role and 1 node with Compute and  another role
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image006.png) Picture of the External ScaleIO Cluster Running
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image007.png) Retrive the external ScaleIO Cluster information. For our example these are the configuration settings:
  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image008.png) Use the ScaleIO Cluster information to update the ScaleIO Plugin information
   ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image009.png)

6.	Apply network settings

7.	Use the networking settings that are appropriate for your environment. For our example we used the default settings provided by Fuel:
   ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image010.png)

8.	Run network verification
   ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image011.png)

9.	Deploy the cluster  ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image012.png)
10. Once the deployment finished successfully open Horizon Portal
 ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image013.png)

11. Check Storage tab under system information and make sure ScaleIO service is up and running
 ![user guide1 ](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image014.png)


ScaleIO Cinder plugin OpenStack operations
==================================================================

Once the OpenStack Cluster is setup, we can setup ScaleIO Volumes. This is an example in how to attach a Volume to a running VM:  

1. Login into the OpenStack Cluster:
 
	![OpenStack Login](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-6.PNG)

2. Review the Block storage services by navigating: Admin -> System -> System Information secction. You should see the ScaleIO Cinder Volume. 
 
	![Block Storage Services Verification](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-7.PNG)

3. Review the System Volumes by navigating to:  Admin -> System -> Volumes. You should see the ScaleIO Volume Type:

	![Volume Type Verification](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-8.PNG)

4. Create a new OpenStack Volume: 
	
	![Volume Creation](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-9.PNG)

5. View the newly created Volume:
	
	![Volume Listing](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-10.PNG)

6. In the ScaleIO Control Panel, you will see that no Volumes have been mapped yet:	

	![ScaleIO UI No mapped Volumes](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-11.PNG)

7. Once the Volume is attached to a VM, the ScaleIO UI will reflect the mapping: 

	![ScaleIO UI Mapped Volume](https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-12.png)


 


.. raw:: pdf

   PageBreak

=========================================================== 
User Guide
===========================================================

#.  Install ScaleIO-Cinder plugin using the `Installation Guide <./installation.rst>`_.

#.  Create environment with enabled plugin in fuel ui, lunch the fuel
    site and check setting section to make sure the Scaleio-Cinder
    section exists

#.  Add 3 nodes with Controller role and 1 node with Compute and another
    role:

    .. image:: images/installation/image006.png
       :width: 50%
#.  Picture of the External ScaleIO Cluster Running:

    .. image:: images/installation/image007.png
       :width: 50%
#.  Retrive the external ScaleIO Cluster information. For
    our example these are the configuration settings:

    .. image:: images/installation/image007.png
       :width: 50%   
   
#.  Use the ScaleIO Cluster information to update the ScaleIO Plugin
    information:

    .. image:: images/installation/image009.png
       :width: 50%
	   
#.  Apply network settings

#.  Use the networking settings that are appropriate for your
    environment. For our example we used the default settings provided
    by Fuel:

    .. image:: images/installation/image010.png
       :width: 50%
	   
#.  Run network verification check:

    .. image:: images/installation/image011.png
       :width: 50%
	   
#.  Deploy the cluster:

    .. image:: images/installation/image012.png
       :width: 50%
	   
#.  Once the deployment finished successfully, open OpenStack Dashboard (Horizon):

    .. image:: images/installation/image013.png
       :width: 50%
	   
#. Check Storage tab under system information and make sure ScaleIO
    service is up and running:

    .. image:: images/installation/image014.png
       :width: 50%
	   
ScaleIO Cinder plugin OpenStack operations
==========================================

Once the OpenStack Cluster is setup, we can setup ScaleIO Volumes. This
is an example in how to attach a Volume to a running VM:

#. Login into the OpenStack Cluster:

    .. image:: images/scaleio-cinder-install-6.PNG
       :alt: OpenStack Login
       :width: 50%
	   
#. Review the Block storage services by navigating: Admin -> System ->
   System Information secction. You should see the ScaleIO Cinder
   Volume.

    .. image:: images/scaleio-cinder-install-7.PNG
       :alt: Block Storage Services Verification
       :width: 50%
	   
#. Review the System Volumes by navigating to: Admin -> System ->
   Volumes. You should see the ScaleIO Volume Type:

    .. image:: images/scaleio-cinder-install-8.PNG
       :alt: Volume Type Verification
       :width: 50%
	   
#. Create a new OpenStack Volume:

    .. image:: images/scaleio-cinder-install-9.PNG
       :alt: Volume Creation
       :width: 50%
	   
#. View the newly created Volume:

    .. image:: images/scaleio-cinder-install-10.PNG
       :alt: Volume Listing
       :width: 50%
	   
#. In the ScaleIO Control Panel, you will see that no Volumes have been
   mapped yet:

    .. image:: images/scaleio-cinder-install-11.PNG
       :alt: ScaleIO UI No mapped Volumes
       :width: 50%

	  
#. Once the Volume is attached to a VM, the ScaleIO UI will reflect the
   mapping:

    .. image:: images/scaleio-cinder-install-12.png
       :alt: ScaleIO UI Mapped Volume
       :width: 50%
	   



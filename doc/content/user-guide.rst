=========================================================== 
User Guide
===========================================================

#.  Install ScaleIO-Cinder plugin using the `Installation Guide <./installation.rst>`_.

#.  Create environment with enabled plugin in fuel ui, lunch the fuel
    site and check setting section to make sure the Scaleio-Cinder
    section exists

#.  Add 3 nodes with Controller role and 1 node with Compute and another
    role:

    .. image:: doc/images/installation/image006.png

#.  Picture of the External ScaleIO Cluster Running:

    .. image:: doc/images/installation/image007.png

#.  Retrive the external ScaleIO Cluster information. For
    our example these are the configuration settings:

    .. image:: doc/images/installation/image008.png

#.  Use the ScaleIO Cluster information to update the ScaleIO Plugin
    information:

    .. image:: doc/images/installation/image009.png

#.  Apply network settings

#.  Use the networking settings that are appropriate for your
    environment. For our example we used the default settings provided
    by Fuel:

    .. image:: doc/images/installation/image010.png

#.  Run network verification check:

    .. image:: doc/images/installation/image011.png

#.  Deploy the cluster:

    .. image:: doc/images/installation/image012.png

#.  Once the deployment finished successfully, open OpenStack Dashboard (Horizon):

    .. image:: doc/images/installation/image013.png

#. Check Storage tab under system information and make sure ScaleIO
    service is up and running:

   .. image:: doc/images/installation/image014.png

ScaleIO Cinder plugin OpenStack operations
==========================================

Once the OpenStack Cluster is setup, we can setup ScaleIO Volumes. This
is an example in how to attach a Volume to a running VM:

#. Login into the OpenStack Cluster:

   .. image:: doc/images/scaleio-cinder-install-6.PNG
      :alt: OpenStack Login

#. Review the Block storage services by navigating: Admin -> System ->
   System Information secction. You should see the ScaleIO Cinder
   Volume.

   .. image:: doc/images/scaleio-cinder-install-7.PNG
      :alt: Block Storage Services Verification

#. Review the System Volumes by navigating to: Admin -> System ->
   Volumes. You should see the ScaleIO Volume Type:

   .. image:: /doc/images/scaleio-cinder-install-8.PNG
      :alt: Volume Type Verification

#. Create a new OpenStack Volume:

   .. image:: doc/images/scaleio-cinder-install-9.PNG
      :alt: Volume Creation

#. View the newly created Volume:

   .. image:: doc/images/scaleio-cinder-install-10.PNG
      :alt: Volume Listing

#. In the ScaleIO Control Panel, you will see that no Volumes have been
   mapped yet:

   .. image:: doc/images/scaleio-cinder-install-11.PNG
      :alt: ScaleIO UI No mapped Volumes

#. Once the Volume is attached to a VM, the ScaleIO UI will reflect the
   mapping:

   .. image:: doc/images/scaleio-cinder-install-12.png
      :alt: ScaleIO UI Mapped Volume




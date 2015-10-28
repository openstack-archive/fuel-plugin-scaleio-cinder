=========================================================== 
User Guide
=========================================================== 
1. Install ScaleIO-Cinder plugin using the `Installation Guide <./installation.rst>`_
2.  Create environment with enabled plugin in fuel ui, lunch the fuel
    site and check setting section to make sure the Scaleio-Cinder
    section exists

3.  Add 3 nodes with Controller role and 1 node with Compute and another
    role |user guide6| Picture of the External ScaleIO Cluster Running
    |user guide7| Retrive the external ScaleIO Cluster information. For
    our example these are the configuration settings: |user guide8| Use
    the ScaleIO Cluster information to update the ScaleIO Plugin
    information |user guide9|

4.  Apply network settings

5.  Use the networking settings that are appropriate for your
    environment. For our example we used the default settings provided
    by Fuel: |user guide10|

6.  Run network verification |user guide11|

7.  Deploy the cluster |user guide12|
8. Once the deployment finished successfully open Horizon Portal |user
    guide13|

9. Check Storage tab under system information and make sure ScaleIO
    service is up and running |user guide14|

ScaleIO Cinder plugin OpenStack operations
==========================================

Once the OpenStack Cluster is setup, we can setup ScaleIO Volumes. This
is an example in how to attach a Volume to a running VM:

1. Login into the OpenStack Cluster:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-6.PNG
      :alt: OpenStack Login

      OpenStack Login

2. Review the Block storage services by navigating: Admin -> System ->
   System Information secction. You should see the ScaleIO Cinder
   Volume.

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-7.PNG
      :alt: Block Storage Services Verification

      Block Storage Services Verification

3. Review the System Volumes by navigating to: Admin -> System ->
   Volumes. You should see the ScaleIO Volume Type:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-8.PNG
      :alt: Volume Type Verification

      Volume Type Verification

4. Create a new OpenStack Volume:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-9.PNG
      :alt: Volume Creation

      Volume Creation

5. View the newly created Volume:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-10.PNG
      :alt: Volume Listing

      Volume Listing

6. In the ScaleIO Control Panel, you will see that no Volumes have been
   mapped yet:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-11.PNG
      :alt: ScaleIO UI No mapped Volumes

      ScaleIO UI No mapped Volumes

7. Once the Volume is attached to a VM, the ScaleIO UI will reflect the
   mapping:

   .. figure:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/scaleio-cinder-install-12.png
      :alt: ScaleIO UI Mapped Volume

      ScaleIO UI Mapped Volume

.. |user guide1| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image001.png
.. |user guide2| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image002.png
.. |user guide3| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image003.png
.. |user guide4| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image004.png
.. |user guide5| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image005.png
.. |user guide6| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image006.png
.. |user guide7| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image007.png
.. |user guide8| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image008.png
.. |user guide9| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image009.png
.. |user guide10| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image010.png
.. |user guide11| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image011.png
.. |user guide12| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image012.png
.. |user guide13| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image013.png
.. |user guide14| image:: https://github.com/openstack/fuel-plugin-scaleio-cinder/blob/master/doc/images/installation/image014.png

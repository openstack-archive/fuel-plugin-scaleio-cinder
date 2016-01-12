# ScaleIO-Cinder Plugin for Fuel

## Overview

The `ScaleIO-Cinder` plugin leverages an existing ScaleIO cluster by configuring Cinder to use ScaleIO as the block storage backend.

If you are looking to deploy a new ScaleIO cluster on Fuel slave nodes and replaces the default OpenStack volume backend by ScaleIO. please take a look at the [ScaleIO](https://github.com/openstack/fuel-plugin-scaleio) plugin.


## Requirements

| Requirement                      | Version/Comment |
|----------------------------------|-----------------|
| Mirantis OpenStack compatibility | 6.1/7.0         |


## Recommendations

None.

## Limitations

The following table shows current limitation
![ScaleIO Support](https://github.com/openstack/fuel-plugin-scaleio-cinder/tree/master/doc/source/images/SIO_Support.png)


# Installation Guide

## ScaleIO-Cinder Plugin install from RPM file

To install the ScaleIO-Cinder plugin, follow these steps:

1. Download the plugin from the [Fuel Plugins Catalog](https://software.mirantis.com/download-mirantis-openstack-fuel-plug-ins/).

2. Copy the plugin file to the Fuel Master node. Follow the [Quick start guide](https://software.mirantis.com/quick-start/) if you don't have a running Fuel Master node yet.
    ```
    $ scp scaleio-cinder-1.0-1.0.0-1.noarch.rpm root@<Fuel Master node IP address>:/tmp/
    ```

3. Log into the Fuel Master node and install the plugin using the fuel command line.
    ```
    $ fuel plugins --install /tmp/scaleio-cinder-1.0-1.0.0-1.noarch.rpm
    ```

4. Verify that the plugin is installed correctly.
    ```
    $ fuel plugins
    ```

## ScaleIO-Cinder Plugin install from source code

To install the ScaleIO-Cinder Plugin from source code, you first need to prepare an environment to build the RPM file of the plugin. The recommended approach is to build the RPM file directly onto the Fuel Master node so that you won't have to copy that file later.

Prepare an environment for building the plugin on the **Fuel Master node**.

1. Install the standard Linux development tools:
    ```
    $ yum install createrepo rpm rpm-build dpkg-devel
    ```

2. Install the Fuel Plugin Builder. To do that, you should first get pip:
    ```
    $ easy_install pip
    ```

3. Then install the Fuel Plugin Builder (the `fpb` command line) with `pip`:
    ```
    $ pip install fuel-plugin-builder
    ```

*Note: You may also have to build the Fuel Plugin Builder if the package version of the
plugin is higher than package version supported by the Fuel Plugin Builder you get from `pypi`.
In this case, please refer to the section "Preparing an environment for plugin development"
of the [Fuel Plugins wiki](https://wiki.openstack.org/wiki/Fuel/Plugins) if you
need further instructions about how to build the Fuel Plugin Builder.*

4. Clone the ScaleIO Plugin git repository:
    ```
    $ git clone --recursive git@github.com:openstack/fuel-plugin-scaleio-cinder.git
    ```

5. Check that the plugin is valid:
    ```
    $ fpb --check ./fuel-plugin-scaleio-cinder
    ```

6. Build the plugin:
    ```
    $ fpb --build ./fuel-plugin-scaleio-cinder
    ```

7. Now you have created an RPM file that you can install using the steps described above. The RPM file will be located in:
    ```
    $ ./fuel-plugin-scaleio-cinder/scaleio-cinder-1.0-1.0.0-1.noarch.rpm
    ```

# User Guide

Please read the [ScaleIO Plugin User Guide](doc).

# Contributions

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) document for the latest information about contributions.

# Bugs, requests, questions

Please use the [Launchpad project site](https://launchpad.net/fuel-plugin-scaleio-cinder) to report bugs, request features, ask questions, etc.

# License

Please read the [LICENSE](LICENSE) document for the latest licensing information.

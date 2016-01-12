#
# Copyright (c) 2011-2015 EMC Corporation
# All Rights Reserved
# EMC Confidential: Restricted Internal Distribution
# 4ebcffbc4faf87cb4da8841bbf214d32f045c8a8.ScaleIO
#

"""Volume drivers for libvirt."""

import errno
import glob
import os
import platform
import re
import time
import urllib2
import urlparse
import requests
import json
import sys
import urllib

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils
import six
import six.moves.urllib.parse as urlparse

from nova.compute import arch
from nova import exception
from nova.i18n import _
from nova.i18n import _LE
from nova.i18n import _LI
from nova.i18n import _LW
from nova.openstack.common import loopingcall
from nova import paths
from nova.storage import linuxscsi
from nova import utils
from nova.virt.libvirt import config as vconfig
from nova.virt.libvirt import quobyte
from nova.virt.libvirt import remotefs
from nova.virt.libvirt import utils as libvirt_utils

LOG = logging.getLogger(__name__)

volume_opts = [
    cfg.IntOpt('num_iscsi_scan_tries',
               default=5,
               help='Number of times to rescan iSCSI target to find volume'),
    cfg.IntOpt('num_iser_scan_tries',
               default=5,
               help='Number of times to rescan iSER target to find volume'),
    cfg.StrOpt('rbd_user',
               help='The RADOS client name for accessing rbd volumes'),
    cfg.StrOpt('rbd_secret_uuid',
               help='The libvirt UUID of the secret for the rbd_user'
                    'volumes'),
    cfg.StrOpt('nfs_mount_point_base',
               default=paths.state_path_def('mnt'),
               help='Directory where the NFS volume is mounted on the'
               ' compute node'),
    cfg.StrOpt('nfs_mount_options',
               help='Mount options passed to the NFS client. See section '
                    'of the nfs man page for details'),
    cfg.StrOpt('smbfs_mount_point_base',
               default=paths.state_path_def('mnt'),
               help='Directory where the SMBFS shares are mounted on the '
                    'compute node'),
    cfg.StrOpt('smbfs_mount_options',
               default='',
               help='Mount options passed to the SMBFS client. See '
                    'mount.cifs man page for details. Note that the '
                    'libvirt-qemu uid and gid must be specified.'),
    cfg.IntOpt('num_aoe_discover_tries',
               default=3,
               help='Number of times to rediscover AoE target to find volume'),
    cfg.StrOpt('glusterfs_mount_point_base',
               default=paths.state_path_def('mnt'),
               help='Directory where the glusterfs volume is mounted on the '
                    'compute node'),
    cfg.BoolOpt('iscsi_use_multipath',
                default=False,
                help='Use multipath connection of the iSCSI volume'),
    cfg.BoolOpt('iser_use_multipath',
                default=False,
                help='Use multipath connection of the iSER volume'),
    cfg.StrOpt('scality_sofs_config',
               help='Path or URL to Scality SOFS configuration file'),
    cfg.StrOpt('scality_sofs_mount_point',
               default='$state_path/scality',
               help='Base dir where Scality SOFS shall be mounted'),
    cfg.ListOpt('qemu_allowed_storage_drivers',
                default=[],
                help='Protocols listed here will be accessed directly '
                     'from QEMU. Currently supported protocols: [gluster]'),
    cfg.StrOpt('quobyte_mount_point_base',
               default=paths.state_path_def('mnt'),
               help='Directory where the Quobyte volume is mounted on the '
                    'compute node'),
    cfg.StrOpt('quobyte_client_cfg',
               help='Path to a Quobyte Client configuration file.'),
    cfg.StrOpt('iscsi_iface',
               deprecated_name='iscsi_transport',
               help='The iSCSI transport iface to use to connect to target in '
                    'case offload support is desired. Supported transports '
                    'are be2iscsi, bnx2i, cxgb3i, cxgb4i, qla4xxx and ocs. '
                    'Default format is transport_name.hwaddress and can be '
                    'generated manually or via iscsiadm -m iface'),
                    # iser is also supported, but use LibvirtISERVolumeDriver
                    # instead
    ]

CONF = cfg.CONF
CONF.register_opts(volume_opts, 'libvirt')


class LibvirtBaseVolumeDriver(object):
    """Base class for volume drivers."""
    def __init__(self, connection, is_block_dev):
        self.connection = connection
        self.is_block_dev = is_block_dev

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = vconfig.LibvirtConfigGuestDisk()
        conf.driver_name = libvirt_utils.pick_disk_driver_name(
            self.connection._host.get_version(),
            self.is_block_dev
        )

        conf.source_device = disk_info['type']
        conf.driver_format = "raw"
        conf.driver_cache = "none"
        conf.target_dev = disk_info['dev']
        conf.target_bus = disk_info['bus']
        conf.serial = connection_info.get('serial')

        # Support for block size tuning
        data = {}
        if 'data' in connection_info:
            data = connection_info['data']
        if 'logical_block_size' in data:
            conf.logical_block_size = data['logical_block_size']
        if 'physical_block_size' in data:
            conf.physical_block_size = data['physical_block_size']

        # Extract rate_limit control parameters
        if 'qos_specs' in data and data['qos_specs']:
            tune_opts = ['total_bytes_sec', 'read_bytes_sec',
                         'write_bytes_sec', 'total_iops_sec',
                         'read_iops_sec', 'write_iops_sec']
            specs = data['qos_specs']
            if isinstance(specs, dict):
                for k, v in specs.iteritems():
                    if k in tune_opts:
                        new_key = 'disk_' + k
                        setattr(conf, new_key, v)
            else:
                LOG.warn(_LW('Unknown content in connection_info/'
                             'qos_specs: %s'), specs)

        # Extract access_mode control parameters
        if 'access_mode' in data and data['access_mode']:
            access_mode = data['access_mode']
            if access_mode in ('ro', 'rw'):
                conf.readonly = access_mode == 'ro'
            else:
                LOG.error(_LE('Unknown content in '
                              'connection_info/access_mode: %s'),
                          access_mode)
                raise exception.InvalidVolumeAccessMode(
                    access_mode=access_mode)

        return conf

    def _get_secret_uuid(self, conf, password=None):
        secret = self.connection._host.find_secret(conf.source_protocol,
                                                   conf.source_name)
        if secret is None:
            secret = self.connection._host.create_secret(conf.source_protocol,
                                                         conf.source_name,
                                                         password)
        return secret.UUIDString()

    def _delete_secret_by_name(self, connection_info):
        source_protocol = connection_info['driver_volume_type']
        netdisk_properties = connection_info['data']
        if source_protocol == 'rbd':
            return
        elif source_protocol == 'iscsi':
            usage_type = 'iscsi'
            usage_name = ("%(target_iqn)s/%(target_lun)s" %
                          netdisk_properties)
            self.connection._host.delete_secret(usage_type, usage_name)

    def connect_volume(self, connection_info, disk_info):
        """Connect the volume. Returns xml for libvirt."""
        pass

    def disconnect_volume(self, connection_info, disk_dev):
        """Disconnect the volume."""
        pass


class LibvirtVolumeDriver(LibvirtBaseVolumeDriver):
    """Class for volumes backed by local file."""
    def __init__(self, connection):
        super(LibvirtVolumeDriver,
              self).__init__(connection, is_block_dev=True)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "block"
        conf.source_path = connection_info['data']['device_path']
        return conf


class LibvirtFakeVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach fake volumes to libvirt."""
    def __init__(self, connection):
        super(LibvirtFakeVolumeDriver,
              self).__init__(connection, is_block_dev=True)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtFakeVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "network"
        conf.source_protocol = "fake"
        conf.source_name = "fake"
        return conf


class LibvirtNetVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach Network volumes to libvirt."""
    def __init__(self, connection):
        super(LibvirtNetVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtNetVolumeDriver,
                     self).get_config(connection_info, disk_info)

        netdisk_properties = connection_info['data']
        conf.source_type = "network"
        conf.source_protocol = connection_info['driver_volume_type']
        conf.source_name = netdisk_properties.get('name')
        conf.source_hosts = netdisk_properties.get('hosts', [])
        conf.source_ports = netdisk_properties.get('ports', [])
        auth_enabled = netdisk_properties.get('auth_enabled')
        if (conf.source_protocol == 'rbd' and
                CONF.libvirt.rbd_secret_uuid):
            conf.auth_secret_uuid = CONF.libvirt.rbd_secret_uuid
            auth_enabled = True  # Force authentication locally
            if CONF.libvirt.rbd_user:
                conf.auth_username = CONF.libvirt.rbd_user
        if conf.source_protocol == 'iscsi':
            try:
                conf.source_name = ("%(target_iqn)s/%(target_lun)s" %
                                    netdisk_properties)
                target_portal = netdisk_properties['target_portal']
            except KeyError:
                raise exception.NovaException(_("Invalid volume source data"))

            ip, port = utils.parse_server_string(target_portal)
            if ip == '' or port == '':
                raise exception.NovaException(_("Invalid target_lun"))
            conf.source_hosts = [ip]
            conf.source_ports = [port]
            if netdisk_properties.get('auth_method') == 'CHAP':
                auth_enabled = True
                conf.auth_secret_type = 'iscsi'
                password = netdisk_properties.get('auth_password')
                conf.auth_secret_uuid = self._get_secret_uuid(conf, password)
        if auth_enabled:
            conf.auth_username = (conf.auth_username or
                                  netdisk_properties['auth_username'])
            conf.auth_secret_type = (conf.auth_secret_type or
                                     netdisk_properties['secret_type'])
            conf.auth_secret_uuid = (conf.auth_secret_uuid or
                                     netdisk_properties['secret_uuid'])
        return conf

    def disconnect_volume(self, connection_info, disk_dev):
        """Detach the volume from instance_name."""
        super(LibvirtNetVolumeDriver,
              self).disconnect_volume(connection_info, disk_dev)
        self._delete_secret_by_name(connection_info)


class LibvirtISCSIVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach Network volumes to libvirt."""
    supported_transports = ['be2iscsi', 'bnx2i', 'cxgb3i',
                            'cxgb4i', 'qla4xxx', 'ocs']

    def __init__(self, connection):
        super(LibvirtISCSIVolumeDriver, self).__init__(connection,
                                                       is_block_dev=True)
        self.num_scan_tries = CONF.libvirt.num_iscsi_scan_tries
        self.use_multipath = CONF.libvirt.iscsi_use_multipath
        if CONF.libvirt.iscsi_iface:
            self.transport = CONF.libvirt.iscsi_iface
        else:
            self.transport = 'default'

    def _get_transport(self):
        if self._validate_transport(self.transport):
            return self.transport
        else:
            return 'default'

    def _validate_transport(self, transport_iface):
        """Check that given iscsi_iface uses only supported transports

        Accepted transport names for provided iface param are
        be2iscsi, bnx2i, cxgb3i, cxgb4i, qla4xxx and ocs. iSER uses it's
        own separate driver. Note the difference between transport and
        iface; unlike iscsi_tcp/iser, this is not one and the same for
        offloaded transports, where the default format is
        transport_name.hwaddress
        """
        # We can support iser here as well, but currently reject it as the
        # separate iser driver has not yet been deprecated.
        if transport_iface == 'default':
            return True
        # Will return (6) if iscsi_iface file was not found, or (2) if iscsid
        # could not be contacted
        out = self._run_iscsiadm_bare(['-m',
                                       'iface',
                                       '-I',
                                       transport_iface],
                                       check_exit_code=[0, 2, 6])[0] or ""
        LOG.debug("iscsiadm %(iface)s configuration: stdout=%(out)s",
                  {'iface': transport_iface, 'out': out})
        for data in [line.split() for line in out.splitlines()]:
            if data[0] == 'iface.transport_name':
                if data[2] in self.supported_transports:
                    return True

        LOG.warn(_LW("No useable transport found for iscsi iface %s. "
                     "Falling back to default transport"),
                 transport_iface)
        return False

    def _run_iscsiadm(self, iscsi_properties, iscsi_command, **kwargs):
        check_exit_code = kwargs.pop('check_exit_code', 0)
        (out, err) = utils.execute('iscsiadm', '-m', 'node', '-T',
                                   iscsi_properties['target_iqn'],
                                   '-p', iscsi_properties['target_portal'],
                                   *iscsi_command, run_as_root=True,
                                   check_exit_code=check_exit_code)
        msg = ('iscsiadm %(command)s: stdout=%(out)s stderr=%(err)s' %
               {'command': iscsi_command, 'out': out, 'err': err})
        # NOTE(bpokorny): iscsi_command can contain passwords so we need to
        # sanitize the password in the message.
        LOG.debug(strutils.mask_password(msg))
        return (out, err)

    def _iscsiadm_update(self, iscsi_properties, property_key, property_value,
                         **kwargs):
        iscsi_command = ('--op', 'update', '-n', property_key,
                         '-v', property_value)
        return self._run_iscsiadm(iscsi_properties, iscsi_command, **kwargs)

    def _get_target_portals_from_iscsiadm_output(self, output):
        # return both portals and iqns
        #
        # as we are parsing a command line utility, allow for the
        # possibility that additional debug data is spewed in the
        # stream, and only grab actual ip / iqn lines.
        targets = []
        for data in [line.split() for line in output.splitlines()]:
            if len(data) == 2 and data[1].startswith('iqn.'):
                targets.append(data)
        return targets

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtISCSIVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "block"
        conf.source_path = connection_info['data']['device_path']
        return conf

    @utils.synchronized('connect_volume')
    def connect_volume(self, connection_info, disk_info):
        """Attach the volume to instance_name."""
        iscsi_properties = connection_info['data']

        # multipath installed, discovering other targets if available
        # multipath should be configured on the nova-compute node,
        # in order to fit storage vendor
        out = None
        if self.use_multipath:
            out = self._run_iscsiadm_discover(iscsi_properties)

            # There are two types of iSCSI multipath devices.  One which shares
            # the same iqn between multiple portals, and the other which use
            # different iqns on different portals.  Try to identify the type by
            # checking the iscsiadm output if the iqn is used by multiple
            # portals.  If it is, it's the former, so use the supplied iqn.
            # Otherwise, it's the latter, so try the ip,iqn combinations to
            # find the targets which constitutes the multipath device.
            ips_iqns = self._get_target_portals_from_iscsiadm_output(out)
            same_portal = False
            all_portals = set()
            match_portals = set()
            for ip, iqn in ips_iqns:
                all_portals.add(ip)
                if iqn == iscsi_properties['target_iqn']:
                    match_portals.add(ip)
            if len(all_portals) == len(match_portals):
                same_portal = True

            for ip, iqn in ips_iqns:
                props = iscsi_properties.copy()
                props['target_portal'] = ip.split(",")[0]
                if not same_portal:
                    props['target_iqn'] = iqn
                self._connect_to_iscsi_portal(props)

            self._rescan_iscsi()
        else:
            self._connect_to_iscsi_portal(iscsi_properties)

            # Detect new/resized LUNs for existing sessions
            self._run_iscsiadm(iscsi_properties, ("--rescan",))

        host_device = self._get_host_device(iscsi_properties)

        # The /dev/disk/by-path/... node is not always present immediately
        # TODO(justinsb): This retry-with-delay is a pattern, move to utils?
        tries = 0
        disk_dev = disk_info['dev']

        # Check host_device only when transport is used, since otherwise it is
        # directly derived from properties. Only needed for unit tests
        while ((self._get_transport() != "default" and not host_device)
          or not os.path.exists(host_device)):
            if tries >= self.num_scan_tries:
                raise exception.NovaException(_("iSCSI device not found at %s")
                                              % (host_device))

            LOG.warn(_LW("ISCSI volume not yet found at: %(disk_dev)s. "
                         "Will rescan & retry.  Try number: %(tries)s"),
                     {'disk_dev': disk_dev, 'tries': tries})

            # The rescan isn't documented as being necessary(?), but it helps
            self._run_iscsiadm(iscsi_properties, ("--rescan",))

            # For offloaded open-iscsi transports, host_device cannot be
            # guessed unlike iscsi_tcp where it can be obtained from
            # properties, so try and get it again.
            if not host_device and self._get_transport() != "default":
                host_device = self._get_host_device(iscsi_properties)

            tries = tries + 1
            if not host_device or not os.path.exists(host_device):
                time.sleep(tries ** 2)

        if tries != 0:
            LOG.debug("Found iSCSI node %(disk_dev)s "
                      "(after %(tries)s rescans)",
                      {'disk_dev': disk_dev,
                       'tries': tries})

        if self.use_multipath:
            # we use the multipath device instead of the single path device
            self._rescan_multipath()

            multipath_device = self._get_multipath_device_name(host_device)

            if multipath_device is not None:
                host_device = multipath_device
                connection_info['data']['multipath_id'] = \
                    multipath_device.split('/')[-1]

        connection_info['data']['device_path'] = host_device

    def _run_iscsiadm_discover(self, iscsi_properties):
        def run_iscsiadm_update_discoverydb():
            return utils.execute(
                            'iscsiadm',
                            '-m', 'discoverydb',
                            '-t', 'sendtargets',
                            '-p', iscsi_properties['target_portal'],
                            '--op', 'update',
                            '-n', "discovery.sendtargets.auth.authmethod",
                            '-v', iscsi_properties['discovery_auth_method'],
                            '-n', "discovery.sendtargets.auth.username",
                            '-v', iscsi_properties['discovery_auth_username'],
                            '-n', "discovery.sendtargets.auth.password",
                            '-v', iscsi_properties['discovery_auth_password'],
                            run_as_root=True)

        out = None
        if iscsi_properties.get('discovery_auth_method'):
            try:
                run_iscsiadm_update_discoverydb()
            except processutils.ProcessExecutionError as exc:
                # iscsiadm returns 6 for "db record not found"
                if exc.exit_code == 6:
                    (out, err) = utils.execute(
                                   'iscsiadm',
                                   '-m', 'discoverydb',
                                   '-t', 'sendtargets',
                                   '-p', iscsi_properties['target_portal'],
                                   '--op', 'new',
                                   run_as_root=True)
                    run_iscsiadm_update_discoverydb()
                else:
                    raise

            out = self._run_iscsiadm_bare(
                                        ['-m',
                                        'discoverydb',
                                        '-t',
                                        'sendtargets',
                                        '-p',
                                        iscsi_properties['target_portal'],
                                        '--discover'],
                                        check_exit_code=[0, 255])[0] or ""
        else:
            out = self._run_iscsiadm_bare(
                                        ['-m',
                                        'discovery',
                                        '-t',
                                        'sendtargets',
                                        '-p',
                                        iscsi_properties['target_portal']],
                                        check_exit_code=[0, 255])[0] or ""
        return out

    @utils.synchronized('connect_volume')
    def disconnect_volume(self, connection_info, disk_dev):
        """Detach the volume from instance_name."""
        iscsi_properties = connection_info['data']
        host_device = self._get_host_device(iscsi_properties)
        multipath_device = None
        if self.use_multipath:
            if 'multipath_id' in iscsi_properties:
                multipath_device = ('/dev/mapper/%s' %
                                    iscsi_properties['multipath_id'])
            else:
                multipath_device = self._get_multipath_device_name(host_device)

        super(LibvirtISCSIVolumeDriver,
              self).disconnect_volume(connection_info, disk_dev)

        if self.use_multipath and multipath_device:
            return self._disconnect_volume_multipath_iscsi(iscsi_properties,
                                                           multipath_device)

        # NOTE(vish): Only disconnect from the target if no luns from the
        #             target are in use.
        device_byname = ("ip-%s-iscsi-%s-lun-" %
                         (iscsi_properties['target_portal'],
                          iscsi_properties['target_iqn']))
        devices = self.connection._get_all_block_devices()
        devices = [dev for dev in devices if (device_byname in dev
                                              and
                                              dev.startswith(
                                                        '/dev/disk/by-path/'))]
        if not devices:
            self._disconnect_from_iscsi_portal(iscsi_properties)
        elif host_device not in devices:
            # Delete device if LUN is not in use by another instance
            self._delete_device(host_device)

    def _delete_device(self, device_path):
        device_name = os.path.basename(os.path.realpath(device_path))
        delete_control = '/sys/block/' + device_name + '/device/delete'
        if os.path.exists(delete_control):
            # Copy '1' from stdin to the device delete control file
            utils.execute('cp', '/dev/stdin', delete_control,
                          process_input='1', run_as_root=True)
        else:
            LOG.warn(_LW("Unable to delete volume device %s"), device_name)

    def _remove_multipath_device_descriptor(self, disk_descriptor):
        disk_descriptor = disk_descriptor.replace('/dev/mapper/', '')
        try:
            self._run_multipath(['-f', disk_descriptor],
                                check_exit_code=[0, 1])
        except processutils.ProcessExecutionError as exc:
            # Because not all cinder drivers need to remove the dev mapper,
            # here just logs a warning to avoid affecting those drivers in
            # exceptional cases.
            LOG.warn(_LW('Failed to remove multipath device descriptor '
                         '%(dev_mapper)s. Exception message: %(msg)s')
                     % {'dev_mapper': disk_descriptor,
                        'msg': exc.message})

    def _disconnect_volume_multipath_iscsi(self, iscsi_properties,
                                           multipath_device):
        self._rescan_iscsi()
        self._rescan_multipath()
        block_devices = self.connection._get_all_block_devices()
        devices = []
        for dev in block_devices:
            if "/mapper/" in dev:
                devices.append(dev)
            else:
                mpdev = self._get_multipath_device_name(dev)
                if mpdev:
                    devices.append(mpdev)

        # Do a discovery to find all targets.
        # Targets for multiple paths for the same multipath device
        # may not be the same.
        out = self._run_iscsiadm_discover(iscsi_properties)

        # Extract targets for the current multipath device.
        ips_iqns = []
        entries = self._get_iscsi_devices()
        for ip, iqn in self._get_target_portals_from_iscsiadm_output(out):
            ip_iqn = "%s-iscsi-%s" % (ip.split(",")[0], iqn)
            for entry in entries:
                entry_ip_iqn = entry.split("-lun-")[0]
                if entry_ip_iqn[:3] == "ip-":
                    entry_ip_iqn = entry_ip_iqn[3:]
                elif entry_ip_iqn[:4] == "pci-":
                    # Look at an offset of len('pci-0000:00:00.0')
                    offset = entry_ip_iqn.find("ip-", 16, 21)
                    entry_ip_iqn = entry_ip_iqn[(offset + 3):]
                if (ip_iqn != entry_ip_iqn):
                    continue
                entry_real_path = os.path.realpath("/dev/disk/by-path/%s" %
                                                   entry)
                entry_mpdev = self._get_multipath_device_name(entry_real_path)
                if entry_mpdev == multipath_device:
                    ips_iqns.append([ip, iqn])
                    break

        if not devices:
            # disconnect if no other multipath devices
            self._disconnect_mpath(iscsi_properties, ips_iqns)
            return

        # Get a target for all other multipath devices
        other_iqns = [self._get_multipath_iqn(device)
                      for device in devices]
        # Get all the targets for the current multipath device
        current_iqns = [iqn for ip, iqn in ips_iqns]

        in_use = False
        for current in current_iqns:
            if current in other_iqns:
                in_use = True
                break

        # If no other multipath device attached has the same iqn
        # as the current device
        if not in_use:
            # disconnect if no other multipath devices with same iqn
            self._disconnect_mpath(iscsi_properties, ips_iqns)
            return
        elif multipath_device not in devices:
            # delete the devices associated w/ the unused multipath
            self._delete_mpath(iscsi_properties, multipath_device, ips_iqns)

        # else do not disconnect iscsi portals,
        # as they are used for other luns,
        # just remove multipath mapping device descriptor
        self._remove_multipath_device_descriptor(multipath_device)
        return

    def _connect_to_iscsi_portal(self, iscsi_properties):
        # NOTE(vish): If we are on the same host as nova volume, the
        #             discovery makes the target so we don't need to
        #             run --op new. Therefore, we check to see if the
        #             target exists, and if we get 255 (Not Found), then
        #             we run --op new. This will also happen if another
        #             volume is using the same target.
        try:
            self._run_iscsiadm(iscsi_properties, ())
        except processutils.ProcessExecutionError as exc:
            # iscsiadm returns 21 for "No records found" after version 2.0-871
            if exc.exit_code in [21, 255]:
                self._reconnect(iscsi_properties)
            else:
                raise

        if iscsi_properties.get('auth_method'):
            self._iscsiadm_update(iscsi_properties,
                                  "node.session.auth.authmethod",
                                  iscsi_properties['auth_method'])
            self._iscsiadm_update(iscsi_properties,
                                  "node.session.auth.username",
                                  iscsi_properties['auth_username'])
            self._iscsiadm_update(iscsi_properties,
                                  "node.session.auth.password",
                                  iscsi_properties['auth_password'])

        # duplicate logins crash iscsiadm after load,
        # so we scan active sessions to see if the node is logged in.
        out = self._run_iscsiadm_bare(["-m", "session"],
                                      run_as_root=True,
                                      check_exit_code=[0, 1, 21])[0] or ""

        portals = [{'portal': p.split(" ")[2], 'iqn': p.split(" ")[3]}
                   for p in out.splitlines() if p.startswith("tcp:")]

        stripped_portal = iscsi_properties['target_portal'].split(",")[0]
        if len(portals) == 0 or len([s for s in portals
                                     if stripped_portal ==
                                     s['portal'].split(",")[0]
                                     and
                                     s['iqn'] ==
                                     iscsi_properties['target_iqn']]
                                    ) == 0:
            try:
                self._run_iscsiadm(iscsi_properties,
                                   ("--login",),
                                   check_exit_code=[0, 255])
            except processutils.ProcessExecutionError as err:
                # as this might be one of many paths,
                # only set successful logins to startup automatically
                if err.exit_code in [15]:
                    self._iscsiadm_update(iscsi_properties,
                                          "node.startup",
                                          "automatic")
                    return

            self._iscsiadm_update(iscsi_properties,
                                  "node.startup",
                                  "automatic")

    def _disconnect_from_iscsi_portal(self, iscsi_properties):
        self._iscsiadm_update(iscsi_properties, "node.startup", "manual",
                              check_exit_code=[0, 21, 255])
        self._run_iscsiadm(iscsi_properties, ("--logout",),
                           check_exit_code=[0, 21, 255])
        self._run_iscsiadm(iscsi_properties, ('--op', 'delete'),
                           check_exit_code=[0, 21, 255])

    def _get_multipath_device_name(self, single_path_device):
        device = os.path.realpath(single_path_device)

        out = self._run_multipath(['-ll',
                                  device],
                                  check_exit_code=[0, 1])[0]
        mpath_line = [line for line in out.splitlines()
                      if "scsi_id" not in line]  # ignore udev errors
        if len(mpath_line) > 0 and len(mpath_line[0]) > 0:
            return "/dev/mapper/%s" % mpath_line[0].split(" ")[0]

        return None

    def _get_iscsi_devices(self):
        try:
            devices = list(os.walk('/dev/disk/by-path'))[0][-1]
        except IndexError:
            return []
        iscsi_devs = []
        for entry in devices:
            if (entry.startswith("ip-") or
                    (entry.startswith('pci-') and 'ip-' in entry)):
                iscsi_devs.append(entry)

        return iscsi_devs

    def _delete_mpath(self, iscsi_properties, multipath_device, ips_iqns):
        entries = self._get_iscsi_devices()
        # Loop through ips_iqns to construct all paths
        iqn_luns = []
        for ip, iqn in ips_iqns:
            iqn_lun = '%s-lun-%s' % (iqn,
                                     iscsi_properties.get('target_lun', 0))
            iqn_luns.append(iqn_lun)
        for dev in ['/dev/disk/by-path/%s' % dev for dev in entries]:
            for iqn_lun in iqn_luns:
                if iqn_lun in dev:
                    self._delete_device(dev)

        self._rescan_multipath()

    def _disconnect_mpath(self, iscsi_properties, ips_iqns):
        for ip, iqn in ips_iqns:
            props = iscsi_properties.copy()
            props['target_portal'] = ip
            props['target_iqn'] = iqn
            self._disconnect_from_iscsi_portal(props)

        self._rescan_multipath()

    def _get_multipath_iqn(self, multipath_device):
        entries = self._get_iscsi_devices()
        for entry in entries:
            entry_real_path = os.path.realpath("/dev/disk/by-path/%s" % entry)
            entry_multipath = self._get_multipath_device_name(entry_real_path)
            if entry_multipath == multipath_device:
                return entry.split("iscsi-")[1].split("-lun")[0]
        return None

    def _run_iscsiadm_bare(self, iscsi_command, **kwargs):
        check_exit_code = kwargs.pop('check_exit_code', 0)
        (out, err) = utils.execute('iscsiadm',
                                   *iscsi_command,
                                   run_as_root=True,
                                   check_exit_code=check_exit_code)
        LOG.debug("iscsiadm %(command)s: stdout=%(out)s stderr=%(err)s",
                  {'command': iscsi_command, 'out': out, 'err': err})
        return (out, err)

    def _run_multipath(self, multipath_command, **kwargs):
        check_exit_code = kwargs.pop('check_exit_code', 0)
        (out, err) = utils.execute('multipath',
                                   *multipath_command,
                                   run_as_root=True,
                                   check_exit_code=check_exit_code)
        LOG.debug("multipath %(command)s: stdout=%(out)s stderr=%(err)s",
                  {'command': multipath_command, 'out': out, 'err': err})
        return (out, err)

    def _rescan_iscsi(self):
        self._run_iscsiadm_bare(('-m', 'node', '--rescan'),
                                check_exit_code=[0, 1, 21, 255])
        self._run_iscsiadm_bare(('-m', 'session', '--rescan'),
                                check_exit_code=[0, 1, 21, 255])

    def _rescan_multipath(self):
        self._run_multipath(['-r'], check_exit_code=[0, 1, 21])

    def _get_host_device(self, transport_properties):
        """Find device path in devtemfs."""
        device = ("ip-%s-iscsi-%s-lun-%s" %
                  (transport_properties['target_portal'],
                   transport_properties['target_iqn'],
                   transport_properties.get('target_lun', 0)))
        if self._get_transport() == "default":
            return ("/dev/disk/by-path/%s" % device)
        else:
            host_device = None
            look_for_device = glob.glob('/dev/disk/by-path/*%s' % device)
            if look_for_device:
                host_device = look_for_device[0]
            return host_device

    def _reconnect(self, iscsi_properties):
        # Note: iscsiadm does not support changing iface.iscsi_ifacename
        # via --op update, so we do this at creation time
        self._run_iscsiadm(iscsi_properties,
                           ('--interface', self._get_transport(),
                            '--op', 'new'))


class LibvirtISERVolumeDriver(LibvirtISCSIVolumeDriver):
    """Driver to attach Network volumes to libvirt."""
    def __init__(self, connection):
        super(LibvirtISERVolumeDriver, self).__init__(connection)
        self.num_scan_tries = CONF.libvirt.num_iser_scan_tries
        self.use_multipath = CONF.libvirt.iser_use_multipath

    def _get_transport(self):
        return 'iser'

    def _get_multipath_iqn(self, multipath_device):
        entries = self._get_iscsi_devices()
        for entry in entries:
            entry_real_path = os.path.realpath("/dev/disk/by-path/%s" % entry)
            entry_multipath = self._get_multipath_device_name(entry_real_path)
            if entry_multipath == multipath_device:
                return entry.split("iser-")[1].split("-lun")[0]
        return None


class LibvirtNFSVolumeDriver(LibvirtBaseVolumeDriver):
    """Class implements libvirt part of volume driver for NFS."""

    def __init__(self, connection):
        """Create back-end to nfs."""
        super(LibvirtNFSVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def _get_device_path(self, connection_info):
        path = os.path.join(CONF.libvirt.nfs_mount_point_base,
            utils.get_hash_str(connection_info['data']['export']))
        path = os.path.join(path, connection_info['data']['name'])
        return path

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtNFSVolumeDriver,
                     self).get_config(connection_info, disk_info)

        conf.source_type = 'file'
        conf.source_path = connection_info['data']['device_path']
        conf.driver_format = connection_info['data'].get('format', 'raw')
        return conf

    def connect_volume(self, connection_info, disk_info):
        """Connect the volume. Returns xml for libvirt."""
        options = connection_info['data'].get('options')
        self._ensure_mounted(connection_info['data']['export'], options)

        connection_info['data']['device_path'] = \
            self._get_device_path(connection_info)

    def disconnect_volume(self, connection_info, disk_dev):
        """Disconnect the volume."""

        export = connection_info['data']['export']
        mount_path = os.path.join(CONF.libvirt.nfs_mount_point_base,
                                  utils.get_hash_str(export))

        try:
            utils.execute('umount', mount_path, run_as_root=True)
        except processutils.ProcessExecutionError as exc:
            if ('device is busy' in exc.message or
                'target is busy' in exc.message):
                LOG.debug("The NFS share %s is still in use.", export)
            else:
                LOG.exception(_LE("Couldn't unmount the NFS share %s"), export)

    def _ensure_mounted(self, nfs_export, options=None):
        """@type nfs_export: string
           @type options: string
        """
        mount_path = os.path.join(CONF.libvirt.nfs_mount_point_base,
                                  utils.get_hash_str(nfs_export))
        if not libvirt_utils.is_mounted(mount_path, nfs_export):
            self._mount_nfs(mount_path, nfs_export, options, ensure=True)
        return mount_path

    def _mount_nfs(self, mount_path, nfs_share, options=None, ensure=False):
        """Mount nfs export to mount path."""
        utils.execute('mkdir', '-p', mount_path)

        # Construct the NFS mount command.
        nfs_cmd = ['mount', '-t', 'nfs']
        if CONF.libvirt.nfs_mount_options is not None:
            nfs_cmd.extend(['-o', CONF.libvirt.nfs_mount_options])
        if options:
            nfs_cmd.extend(options.split(' '))
        nfs_cmd.extend([nfs_share, mount_path])

        try:
            utils.execute(*nfs_cmd, run_as_root=True)
        except processutils.ProcessExecutionError as exc:
            if ensure and 'already mounted' in exc.message:
                LOG.warn(_LW("%s is already mounted"), nfs_share)
            else:
                raise


class LibvirtSMBFSVolumeDriver(LibvirtBaseVolumeDriver):
    """Class implements libvirt part of volume driver for SMBFS."""

    def __init__(self, connection):
        super(LibvirtSMBFSVolumeDriver,
              self).__init__(connection, is_block_dev=False)
        self.username_regex = re.compile(
            r"(user(?:name)?)=(?:[^ ,]+\\)?([^ ,]+)")

    def _get_device_path(self, connection_info):
        smbfs_share = connection_info['data']['export']
        mount_path = self._get_mount_path(smbfs_share)
        volume_path = os.path.join(mount_path,
                                   connection_info['data']['name'])
        return volume_path

    def _get_mount_path(self, smbfs_share):
        mount_path = os.path.join(CONF.libvirt.smbfs_mount_point_base,
                                  utils.get_hash_str(smbfs_share))
        return mount_path

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtSMBFSVolumeDriver,
                     self).get_config(connection_info, disk_info)

        conf.source_type = 'file'
        conf.driver_cache = 'writethrough'
        conf.source_path = connection_info['data']['device_path']
        conf.driver_format = connection_info['data'].get('format', 'raw')
        return conf

    def connect_volume(self, connection_info, disk_info):
        """Connect the volume."""
        smbfs_share = connection_info['data']['export']
        mount_path = self._get_mount_path(smbfs_share)

        if not libvirt_utils.is_mounted(mount_path, smbfs_share):
            mount_options = self._parse_mount_options(connection_info)
            remotefs.mount_share(mount_path, smbfs_share,
                                 export_type='cifs', options=mount_options)

        device_path = self._get_device_path(connection_info)
        connection_info['data']['device_path'] = device_path

    def disconnect_volume(self, connection_info, disk_dev):
        """Disconnect the volume."""
        smbfs_share = connection_info['data']['export']
        mount_path = self._get_mount_path(smbfs_share)
        remotefs.unmount_share(mount_path, smbfs_share)

    def _parse_mount_options(self, connection_info):
        mount_options = " ".join(
            [connection_info['data'].get('options') or '',
             CONF.libvirt.smbfs_mount_options])

        if not self.username_regex.findall(mount_options):
            mount_options = mount_options + ' -o username=guest'
        else:
            # Remove the Domain Name from user name
            mount_options = self.username_regex.sub(r'\1=\2', mount_options)
        return mount_options.strip(", ").split(' ')


class LibvirtAOEVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach AoE volumes to libvirt."""
    def __init__(self, connection):
        super(LibvirtAOEVolumeDriver,
              self).__init__(connection, is_block_dev=True)

    def _aoe_discover(self):
        """Call aoe-discover (aoe-tools) AoE Discover."""
        (out, err) = utils.execute('aoe-discover',
                                   run_as_root=True, check_exit_code=0)
        return (out, err)

    def _aoe_revalidate(self, aoedev):
        """Revalidate the LUN Geometry (When an AoE ID is reused)."""
        (out, err) = utils.execute('aoe-revalidate', aoedev,
                                   run_as_root=True, check_exit_code=0)
        return (out, err)

    def _get_device_path(self, connection_info):
        shelf = connection_info['data']['target_shelf']
        lun = connection_info['data']['target_lun']
        aoedev = 'e%s.%s' % (shelf, lun)
        aoedevpath = '/dev/etherd/%s' % (aoedev)
        return aoedevpath

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtAOEVolumeDriver,
                     self).get_config(connection_info, disk_info)

        conf.source_type = "block"
        conf.source_path = connection_info['data']['device_path']
        return conf

    def connect_volume(self, connection_info, mount_device):
        shelf = connection_info['data']['target_shelf']
        lun = connection_info['data']['target_lun']
        aoedev = 'e%s.%s' % (shelf, lun)
        aoedevpath = '/dev/etherd/%s' % (aoedev)

        if os.path.exists(aoedevpath):
            # NOTE(jbr_): If aoedevpath already exists, revalidate the LUN.
            self._aoe_revalidate(aoedev)
        else:
            # NOTE(jbr_): If aoedevpath does not exist, do a discover.
            self._aoe_discover()

        # NOTE(jbr_): Device path is not always present immediately
        def _wait_for_device_discovery(aoedevpath, mount_device):
            tries = self.tries
            if os.path.exists(aoedevpath):
                raise loopingcall.LoopingCallDone()

            if self.tries >= CONF.libvirt.num_aoe_discover_tries:
                raise exception.NovaException(_("AoE device not found at %s") %
                                                (aoedevpath))
            LOG.warn(_LW("AoE volume not yet found at: %(aoedevpath)s. "
                         "Try number: %(tries)s"),
                     {'aoedevpath': aoedevpath, 'tries': tries})

            self._aoe_discover()
            self.tries = self.tries + 1

        self.tries = 0
        timer = loopingcall.FixedIntervalLoopingCall(
            _wait_for_device_discovery, aoedevpath, mount_device)
        timer.start(interval=2).wait()

        tries = self.tries
        if tries != 0:
            LOG.debug("Found AoE device %(aoedevpath)s "
                      "(after %(tries)s rediscover)",
                      {'aoedevpath': aoedevpath,
                       'tries': tries})

        connection_info['data']['device_path'] = \
            self._get_device_path(connection_info)


class LibvirtGlusterfsVolumeDriver(LibvirtBaseVolumeDriver):
    """Class implements libvirt part of volume driver for GlusterFS."""

    def __init__(self, connection):
        """Create back-end to glusterfs."""
        super(LibvirtGlusterfsVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def _get_device_path(self, connection_info):
        path = os.path.join(CONF.libvirt.glusterfs_mount_point_base,
            utils.get_hash_str(connection_info['data']['export']))
        path = os.path.join(path, connection_info['data']['name'])
        return path

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtGlusterfsVolumeDriver,
                     self).get_config(connection_info, disk_info)

        data = connection_info['data']

        if 'gluster' in CONF.libvirt.qemu_allowed_storage_drivers:
            vol_name = data['export'].split('/')[1]
            source_host = data['export'].split('/')[0][:-1]

            conf.source_ports = ['24007']
            conf.source_type = 'network'
            conf.source_protocol = 'gluster'
            conf.source_hosts = [source_host]
            conf.source_name = '%s/%s' % (vol_name, data['name'])
        else:
            conf.source_type = 'file'
            conf.source_path = connection_info['data']['device_path']

        conf.driver_format = connection_info['data'].get('format', 'raw')

        return conf

    def connect_volume(self, connection_info, mount_device):
        data = connection_info['data']

        if 'gluster' not in CONF.libvirt.qemu_allowed_storage_drivers:
            self._ensure_mounted(data['export'], data.get('options'))
            connection_info['data']['device_path'] = \
                self._get_device_path(connection_info)

    def disconnect_volume(self, connection_info, disk_dev):
        """Disconnect the volume."""

        if 'gluster' in CONF.libvirt.qemu_allowed_storage_drivers:
            return

        export = connection_info['data']['export']
        mount_path = os.path.join(CONF.libvirt.glusterfs_mount_point_base,
                                  utils.get_hash_str(export))

        try:
            utils.execute('umount', mount_path, run_as_root=True)
        except processutils.ProcessExecutionError as exc:
            if 'target is busy' in exc.message:
                LOG.debug("The GlusterFS share %s is still in use.", export)
            else:
                LOG.exception(_LE("Couldn't unmount the GlusterFS share %s"),
                              export)

    def _ensure_mounted(self, glusterfs_export, options=None):
        """@type glusterfs_export: string
           @type options: string
        """
        mount_path = os.path.join(CONF.libvirt.glusterfs_mount_point_base,
                                  utils.get_hash_str(glusterfs_export))
        if not libvirt_utils.is_mounted(mount_path, glusterfs_export):
            self._mount_glusterfs(mount_path, glusterfs_export,
                                  options, ensure=True)
        return mount_path

    def _mount_glusterfs(self, mount_path, glusterfs_share,
                         options=None, ensure=False):
        """Mount glusterfs export to mount path."""
        utils.execute('mkdir', '-p', mount_path)

        gluster_cmd = ['mount', '-t', 'glusterfs']
        if options is not None:
            gluster_cmd.extend(options.split(' '))
        gluster_cmd.extend([glusterfs_share, mount_path])

        try:
            utils.execute(*gluster_cmd, run_as_root=True)
        except processutils.ProcessExecutionError as exc:
            if ensure and 'already mounted' in exc.message:
                LOG.warn(_LW("%s is already mounted"), glusterfs_share)
            else:
                raise


class LibvirtFibreChannelVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach Fibre Channel Network volumes to libvirt."""

    def __init__(self, connection):
        super(LibvirtFibreChannelVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def _get_pci_num(self, hba):
        # NOTE(walter-boring)
        # device path is in format of
        # /sys/devices/pci0000:00/0000:00:03.0/0000:05:00.3/host2/fc_host/host2
        # sometimes an extra entry exists before the host2 value
        # we always want the value prior to the host2 value
        pci_num = None
        if hba is not None:
            if "device_path" in hba:
                index = 0
                device_path = hba['device_path'].split('/')
                for value in device_path:
                    if value.startswith('host'):
                        break
                    index = index + 1

                if index > 0:
                    pci_num = device_path[index - 1]

        return pci_num

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtFibreChannelVolumeDriver,
                     self).get_config(connection_info, disk_info)

        conf.source_type = "block"
        conf.source_path = connection_info['data']['device_path']
        return conf

    def _get_lun_string_for_s390(self, lun):
        target_lun = 0
        if lun < 256:
            target_lun = "0x00%02x000000000000" % lun
        elif lun <= 0xffffffff:
            target_lun = "0x%08x00000000" % lun
        return target_lun

    def _get_device_file_path_s390(self, pci_num, target_wwn, lun):
        """Returns device file path"""
        # NOTE the format of device file paths depends on the system
        # architecture. Most architectures use a PCI based format.
        # Systems following the S390, or S390x architecture use a format
        # which is based upon the inherent channel architecture (ccw).
        host_device = ("/dev/disk/by-path/ccw-%s-zfcp-%s:%s" %
                        (pci_num,
                        target_wwn,
                        lun))
        return host_device

    def _remove_lun_from_s390(self, connection_info):
        """Rempove lun from s390 configuration"""
        # If LUN scanning is turned off on systems following the s390, or
        # s390x architecture LUNs need to be removed from the configuration
        # using the unit_remove call. The unit_remove call needs to be issued
        # for each (virtual) HBA and target_port.
        fc_properties = connection_info['data']
        lun = int(fc_properties.get('target_lun', 0))
        target_lun = self._get_lun_string_for_s390(lun)
        ports = fc_properties['target_wwn']

        for device_num, target_wwn in self._get_possible_devices(ports):
            libvirt_utils.perform_unit_remove_for_s390(device_num,
                                              target_wwn,
                                              target_lun)

    def _get_possible_devices(self, wwnports):
        """Compute the possible valid fiber channel device options.

        :param wwnports: possible wwn addresses. Can either be string
        or list of strings.

        :returns: list of (pci_id, wwn) tuples

        Given one or more wwn (mac addresses for fiber channel) ports
        do the matrix math to figure out a set of pci device, wwn
        tuples that are potentially valid (they won't all be). This
        provides a search space for the device connection.

        """
        # the wwn (think mac addresses for fiber channel devices) can
        # either be a single value or a list. Normalize it to a list
        # for further operations.
        wwns = []
        if isinstance(wwnports, list):
            for wwn in wwnports:
                wwns.append(str(wwn))
        elif isinstance(wwnports, six.string_types):
            wwns.append(str(wwnports))

        raw_devices = []
        hbas = libvirt_utils.get_fc_hbas_info()
        for hba in hbas:
            pci_num = self._get_pci_num(hba)
            if pci_num is not None:
                for wwn in wwns:
                    target_wwn = "0x%s" % wwn.lower()
                    raw_devices.append((pci_num, target_wwn))
        return raw_devices

    @utils.synchronized('connect_volume')
    def connect_volume(self, connection_info, disk_info):
        """Attach the volume to instance_name."""
        fc_properties = connection_info['data']
        mount_device = disk_info["dev"]

        possible_devs = self._get_possible_devices(fc_properties['target_wwn'])
        # map the raw device possibilities to possible host device paths
        host_devices = []
        for device in possible_devs:
            pci_num, target_wwn = device
            if platform.machine() in (arch.S390, arch.S390X):
                target_lun = self._get_lun_string_for_s390(
                                fc_properties.get('target_lun', 0))
                host_device = self._get_device_file_path_s390(
                                pci_num,
                                target_wwn,
                                target_lun)
                libvirt_utils.perform_unit_add_for_s390(
                                pci_num, target_wwn, target_lun)
            else:
                host_device = ("/dev/disk/by-path/pci-%s-fc-%s-lun-%s" %
                           (pci_num,
                            target_wwn,
                            fc_properties.get('target_lun', 0)))
            host_devices.append(host_device)

        if len(host_devices) == 0:
            # this is empty because we don't have any FC HBAs
            msg = _("We are unable to locate any Fibre Channel devices")
            raise exception.NovaException(msg)

        # The /dev/disk/by-path/... node is not always present immediately
        # We only need to find the first device.  Once we see the first device
        # multipath will have any others.
        def _wait_for_device_discovery(host_devices, mount_device):
            tries = self.tries
            for device in host_devices:
                LOG.debug("Looking for Fibre Channel dev %(device)s",
                          {'device': device})
                if os.path.exists(device):
                    self.host_device = device
                    # get the /dev/sdX device.  This is used
                    # to find the multipath device.
                    self.device_name = os.path.realpath(device)
                    raise loopingcall.LoopingCallDone()

            if self.tries >= CONF.libvirt.num_iscsi_scan_tries:
                msg = _("Fibre Channel device not found.")
                raise exception.NovaException(msg)

            LOG.warn(_LW("Fibre volume not yet found at: %(mount_device)s. "
                         "Will rescan & retry.  Try number: %(tries)s"),
                     {'mount_device': mount_device, 'tries': tries})

            linuxscsi.rescan_hosts(libvirt_utils.get_fc_hbas_info())
            self.tries = self.tries + 1

        self.host_device = None
        self.device_name = None
        self.tries = 0
        timer = loopingcall.FixedIntervalLoopingCall(
            _wait_for_device_discovery, host_devices, mount_device)
        timer.start(interval=2).wait()

        tries = self.tries
        if self.host_device is not None and self.device_name is not None:
            LOG.debug("Found Fibre Channel volume %(mount_device)s "
                      "(after %(tries)s rescans)",
                      {'mount_device': mount_device,
                       'tries': tries})

        # see if the new drive is part of a multipath
        # device.  If so, we'll use the multipath device.
        mdev_info = linuxscsi.find_multipath_device(self.device_name)
        if mdev_info is not None:
            LOG.debug("Multipath device discovered %(device)s",
                      {'device': mdev_info['device']})
            device_path = mdev_info['device']
            connection_info['data']['device_path'] = device_path
            connection_info['data']['devices'] = mdev_info['devices']
            connection_info['data']['multipath_id'] = mdev_info['id']
        else:
            # we didn't find a multipath device.
            # so we assume the kernel only sees 1 device
            device_path = self.host_device
            device_info = linuxscsi.get_device_info(self.device_name)
            connection_info['data']['device_path'] = device_path
            connection_info['data']['devices'] = [device_info]

    @utils.synchronized('connect_volume')
    def disconnect_volume(self, connection_info, mount_device):
        """Detach the volume from instance_name."""
        super(LibvirtFibreChannelVolumeDriver,
              self).disconnect_volume(connection_info, mount_device)

        # If this is a multipath device, we need to search again
        # and make sure we remove all the devices. Some of them
        # might not have shown up at attach time.
        if 'multipath_id' in connection_info['data']:
            multipath_id = connection_info['data']['multipath_id']
            mdev_info = linuxscsi.find_multipath_device(multipath_id)
            devices = mdev_info['devices']
            LOG.debug("devices to remove = %s", devices)
        else:
            # only needed when multipath-tools work improperly
            devices = connection_info['data'].get('devices', [])
            LOG.warn(_LW("multipath-tools probably work improperly. "
                       "devices to remove = %s.") % devices)

        # There may have been more than 1 device mounted
        # by the kernel for this volume.  We have to remove
        # all of them
        for device in devices:
            linuxscsi.remove_device(device)
        if platform.machine() in (arch.S390, arch.S390X):
            self._remove_lun_from_s390(connection_info)


class LibvirtScalityVolumeDriver(LibvirtBaseVolumeDriver):
    """Scality SOFS Nova driver. Provide hypervisors with access
    to sparse files on SOFS.
    """

    def __init__(self, connection):
        """Create back-end to SOFS and check connection."""
        super(LibvirtScalityVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def _get_device_path(self, connection_info):
        path = os.path.join(CONF.libvirt.scality_sofs_mount_point,
                            connection_info['data']['sofs_path'])
        return path

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtScalityVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = 'file'
        conf.source_path = connection_info['data']['device_path']

        # The default driver cache policy is 'none', and this causes
        # qemu/kvm to open the volume file with O_DIRECT, which is
        # rejected by FUSE (on kernels older than 3.3). Scality SOFS
        # is FUSE based, so we must provide a more sensible default.
        conf.driver_cache = 'writethrough'

        return conf

    def connect_volume(self, connection_info, disk_info):
        """Connect the volume. Returns xml for libvirt."""
        self._check_prerequisites()
        self._mount_sofs()

        connection_info['data']['device_path'] = \
            self._get_device_path(connection_info)

    def _check_prerequisites(self):
        """Sanity checks before attempting to mount SOFS."""

        # config is mandatory
        config = CONF.libvirt.scality_sofs_config
        if not config:
            msg = _LW("Value required for 'scality_sofs_config'")
            LOG.warn(msg)
            raise exception.NovaException(msg)

        # config can be a file path or a URL, check it
        if urlparse.urlparse(config).scheme == '':
            # turn local path into URL
            config = 'file://%s' % config
        try:
            urllib2.urlopen(config, timeout=5).close()
        except urllib2.URLError as e:
            msg = _LW("Cannot access 'scality_sofs_config': %s") % e
            LOG.warn(msg)
            raise exception.NovaException(msg)

        # mount.sofs must be installed
        if not os.access('/sbin/mount.sofs', os.X_OK):
            msg = _LW("Cannot execute /sbin/mount.sofs")
            LOG.warn(msg)
            raise exception.NovaException(msg)

    def _mount_sofs(self):
        config = CONF.libvirt.scality_sofs_config
        mount_path = CONF.libvirt.scality_sofs_mount_point
        sysdir = os.path.join(mount_path, 'sys')

        if not os.path.isdir(mount_path):
            utils.execute('mkdir', '-p', mount_path)
        if not os.path.isdir(sysdir):
            utils.execute('mount', '-t', 'sofs', config, mount_path,
                          run_as_root=True)
        if not os.path.isdir(sysdir):
            msg = _LW("Cannot mount Scality SOFS, check syslog for errors")
            LOG.warn(msg)
            raise exception.NovaException(msg)


class LibvirtGPFSVolumeDriver(LibvirtBaseVolumeDriver):
    """Class for volumes backed by gpfs volume."""
    def __init__(self, connection):
        super(LibvirtGPFSVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtGPFSVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "file"
        conf.source_path = connection_info['data']['device_path']
        return conf


class LibvirtQuobyteVolumeDriver(LibvirtBaseVolumeDriver):
    """Class implements libvirt part of volume driver for Quobyte."""

    def __init__(self, connection):
        """Create back-end to Quobyte."""
        super(LibvirtQuobyteVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def get_config(self, connection_info, disk_info):
        conf = super(LibvirtQuobyteVolumeDriver,
                     self).get_config(connection_info, disk_info)
        data = connection_info['data']
        conf.source_protocol = quobyte.SOURCE_PROTOCOL
        conf.source_type = quobyte.SOURCE_TYPE
        conf.driver_cache = quobyte.DRIVER_CACHE
        conf.driver_io = quobyte.DRIVER_IO
        conf.driver_format = data.get('format', 'raw')

        quobyte_volume = self._normalize_url(data['export'])
        path = os.path.join(self._get_mount_point_for_share(quobyte_volume),
                            data['name'])
        conf.source_path = path

        return conf

    @utils.synchronized('connect_volume')
    def connect_volume(self, connection_info, disk_info):
        """Connect the volume."""
        data = connection_info['data']
        quobyte_volume = self._normalize_url(data['export'])
        mount_path = self._get_mount_point_for_share(quobyte_volume)
        mounted = libvirt_utils.is_mounted(mount_path,
                                           quobyte.SOURCE_PROTOCOL
                                           + '@' + quobyte_volume)
        if mounted:
            try:
                os.stat(mount_path)
            except OSError as exc:
                if exc.errno == errno.ENOTCONN:
                    mounted = False
                    LOG.info(_LI('Fixing previous mount %s which was not'
                                 ' unmounted correctly.'), mount_path)
                    quobyte.umount_volume(mount_path)

        if not mounted:
            quobyte.mount_volume(quobyte_volume,
                                 mount_path,
                                 CONF.libvirt.quobyte_client_cfg)

        quobyte.validate_volume(mount_path)

    @utils.synchronized('connect_volume')
    def disconnect_volume(self, connection_info, disk_dev):
        """Disconnect the volume."""

        quobyte_volume = self._normalize_url(connection_info['data']['export'])
        mount_path = self._get_mount_point_for_share(quobyte_volume)

        if libvirt_utils.is_mounted(mount_path, 'quobyte@' + quobyte_volume):
            quobyte.umount_volume(mount_path)
        else:
            LOG.info(_LI("Trying to disconnected unmounted volume at %s"),
                     mount_path)

    def _normalize_url(self, export):
        protocol = quobyte.SOURCE_PROTOCOL + "://"
        if export.startswith(protocol):
            export = export[len(protocol):]
        return export

    def _get_mount_point_for_share(self, quobyte_volume):
        """Return mount point for Quobyte volume.

        :param quobyte_volume: Example: storage-host/openstack-volumes
        """
        return os.path.join(CONF.libvirt.quobyte_mount_point_base,
                            utils.get_hash_str(quobyte_volume))
        

class LibvirtScaleIOVolumeDriver(LibvirtBaseVolumeDriver):

    """Class implements libvirt part of volume driver
     for ScaleIO cinder driver."""
    local_sdc_id = None
    mdm_id = None
    pattern3 = None

    def __init__(self, connection):
        """Create back-end to nfs."""
        LOG.warning("ScaleIO libvirt volume driver INIT")
        super(LibvirtScaleIOVolumeDriver,
              self).__init__(connection, is_block_dev=False)

    def find_volume_path(self, volume_id):

        LOG.info("looking for volume %s" % volume_id)
        # look for the volume in /dev/disk/by-id directory
        disk_filename = ""
        tries = 0
        while not disk_filename:
            if (tries > 15):
                raise exception.NovaException(
                    "scaleIO volume {0} not found at expected \
                    path ".format(volume_id))
            by_id_path = "/dev/disk/by-id"
            if not os.path.isdir(by_id_path):
                LOG.warn(
                    "scaleIO volume {0} not yet found (no directory \
                    /dev/disk/by-id yet). Try number: {1} ".format(
                        volume_id,
                        tries))
                tries = tries + 1
                time.sleep(1)
                continue
            filenames = os.listdir(by_id_path)
            LOG.warning(
                "Files found in {0} path: {1} ".format(
                    by_id_path,
                    filenames))
            for filename in filenames:
                if (filename.startswith("emc-vol") and
                        filename.endswith(volume_id)):
                    disk_filename = filename
            if not disk_filename:
                LOG.warn(
                    "scaleIO volume {0} not yet found. \
                    Try number: {1} ".format(
                        volume_id,
                        tries))
                tries = tries + 1
                time.sleep(1)

        if (tries != 0):
            LOG.warning(
                "Found scaleIO device {0} after {1} retries ".format(
                    disk_filename,
                    tries))
        full_disk_name = by_id_path + "/" + disk_filename
        LOG.warning("Full disk name is " + full_disk_name)
        return full_disk_name
#         path = os.path.realpath(full_disk_name)
#         LOG.warning("Path is " + path)
#         return path

    def _get_client_id(self, server_ip, server_port,
                       server_username, server_password, server_token, sdc_ip):
        request = "https://" + server_ip + ":" + server_port + \
            "/api/types/Client/instances/getByIp::" + sdc_ip + "/"
        LOG.info("ScaleIO get client id by ip request: %s" % request)
        r = requests.get(
            request,
            auth=(
                server_username,
                server_token),
            verify=False)
        r = self._check_response(
            r,
            request,
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token)

        sdc_id = r.json()
        if (sdc_id == '' or sdc_id is None):
            msg = ("Client with ip %s wasn't found " % (sdc_ip))
            LOG.error(msg)
            raise exception.NovaException(data=msg)
        if (r.status_code != 200 and "errorCode" in sdc_id):
            msg = (
                "Error getting sdc id from ip %s: %s " %
                (sdc_ip, sdc_id['message']))
            LOG.error(msg)
            raise exception.NovaException(data=msg)
        LOG.info("ScaleIO sdc id is %s" % sdc_id)
        return sdc_id

    def _get_volume_id(self, server_ip, server_port,
                       server_username, server_password,
                       server_token, volname):
        volname_encoded = urllib.quote(volname, '')
        volname_double_encoded = urllib.quote(volname_encoded, '')
#         volname = volname.replace('/', '%252F')
        LOG.info(
            "volume name after double encoding is %s " %
            volname_double_encoded)
        request = "https://" + server_ip + ":" + server_port + \
            "/api/types/Volume/instances/getByName::" + volname_double_encoded
        LOG.info("ScaleIO get volume id by name request: %s" % request)
        r = requests.get(
            request,
            auth=(
                server_username,
                server_token),
            verify=False)
        r = self._check_response(
            r,
            request,
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token)

        volume_id = r.json()
        if (volume_id == '' or volume_id is None):
            msg = ("Volume with name %s wasn't found " % (volname))
            LOG.error(msg)
            raise exception.NovaException(data=msg)
        if (r.status_code != 200 and "errorCode" in volume_id):
            msg = (
                "Error getting volume id from name %s: %s " %
                (volname, volume_id['message']))
            LOG.error(msg)
            raise exception.NovaException(data=msg)
        LOG.info("ScaleIO volume id is %s" % volume_id)
        return volume_id

    def _check_response(self, response, request, server_ip,
                        server_port, server_username,
                        server_password, server_token, isGetRequest=True, params=None):
        if (response.status_code == 401 or response.status_code == 403):
            LOG.info("Token is invalid, going to re-login and get a new one")
            login_request = "https://" + server_ip + \
                ":" + server_port + "/api/login"
            r = requests.get(
                login_request,
                auth=(
                    server_username,
                    server_password),
                verify=False)
            token = r.json()
            # repeat request with valid token
            LOG.debug(
                "going to perform request again {0} \
                with valid token".format(request))
            if isGetRequest:
                res = requests.get(
                                   request,
                                   auth=(
                                         server_username,
                                         token),
                                   verify=False)
            else:
                headers = {'content-type': 'application/json'}
                res = requests.post(
                                  request,
                                  data=json.dumps(params),
                                  headers=headers,
                                  auth=(
                                        server_username,
                                        token),
                                  verify=False)
            return res
        return response

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtScaleIOVolumeDriver,
                     self).get_config(connection_info,
                                      disk_info)
        conf.source_type = 'block'
        volname = connection_info['data']['scaleIO_volname']
        server_ip = connection_info['data']['serverIP']
        server_port = connection_info['data']['serverPort']
        server_username = connection_info['data']['serverUsername']
        server_password = connection_info['data']['serverPassword']
        server_token = connection_info['data']['serverToken']
        volume_id = self._get_volume_id(
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token,
            volname)
        conf.source_path = self.find_volume_path(volume_id)
        return conf

    def connect_volume(self, connection_info, disk_info):
        """Connect the volume. Returns xml for libvirt."""
        conf = super(LibvirtScaleIOVolumeDriver,
                     self).get_config(connection_info,
                                          disk_info)
        LOG.info("scaleIO connect volume in scaleio libvirt volume driver")
        data = connection_info
        LOG.info("scaleIO connect to stuff " + str(data))
        data = connection_info['data']
#         LOG.info("scaleIO connect to joined "+str(data))
#         LOG.info("scaleIO Dsk info "+str(disk_info))
        volname = connection_info['data']['scaleIO_volname']
        # sdc ip here is wrong, probably not retrieved properly in cinder
        # driver. Currently not used.
        sdc_ip = connection_info['data']['hostIP']
        server_ip = connection_info['data']['serverIP']
        server_port = connection_info['data']['serverPort']
        server_username = connection_info['data']['serverUsername']
        server_password = connection_info['data']['serverPassword']
        server_token = connection_info['data']['serverToken']
        iops_limit = connection_info['data']['iopsLimit']
        bandwidth_limit = connection_info['data']['bandwidthLimit']
        LOG.debug(
            "scaleIO Volume name: {0}, SDC IP: {1}, REST Server IP: {2}, \
            REST Server username: {3}, REST Server password: {4}, iops limit: \
            {5}, bandwidth limit: {6}".format(
                volname,
                sdc_ip,
                server_ip,
                server_username,
                server_password,
                iops_limit,
                bandwidth_limit))

        cmd = ['drv_cfg']
        cmd += ["--query_guid"]

        LOG.info("ScaleIO sdc query guid command: " + str(cmd))

        try:
            (out, err) = utils.execute(*cmd, run_as_root=True)
            LOG.info("map volume %s: stdout=%s stderr=%s" % (cmd, out, err))
        except processutils.ProcessExecutionError as e:
            msg = ("Error querying sdc guid: %s" % (e.stderr))
            LOG.error(msg)
            raise exception.NovaException(data=msg)

        guid = out
        msg = ("Current sdc guid: %s" % (guid))
        LOG.info(msg)

#         sdc_id = self._get_client_id(server_ip, server_port, \
#         server_username, server_password, server_token, sdc_ip)

#         params = {'sdcId' : sdc_id}

        params = {'guid': guid, 'allowMultipleMappings': 'TRUE'}

        volume_id = self._get_volume_id(
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token,
            volname)
        headers = {'content-type': 'application/json'}
        request = "https://" + server_ip + ":" + server_port + \
            "/api/instances/Volume::" + str(volume_id) + "/action/addMappedSdc"
        LOG.info("map volume request: %s" % request)
        r = requests.post(
            request,
            data=json.dumps(params),
            headers=headers,
            auth=(
                server_username,
                server_token),
            verify=False)
        r = self._check_response(
            r,
            request,
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token,
            False,
            params)
#         LOG.info("map volume response: %s" % r.text)

        if (r.status_code != 200):
            response = r.json()
            error_code = response['errorCode']
            if (error_code == 81):
                msg = (
                    "Ignoring error mapping volume %s: volume already mapped" %
                    (volname))
                LOG.warning(msg)
            else:
                msg = (
                    "Error mapping volume %s: %s" %
                    (volname, response['message']))
                LOG.error(msg)
                raise exception.NovaException(data=msg)

#       convert id to hex
#         val = int(volume_id)
#         id_in_hex = hex((val + (1 << 64)) % (1 << 64))
#         formated_id = id_in_hex.rstrip("L").lstrip("0x") or "0"
        formated_id = volume_id

        conf.source_path = self.find_volume_path(formated_id)
        conf.source_type = 'block'

#       set QoS settings after map was performed
        if (iops_limit is not None or bandwidth_limit is not None):
            params = {
                'guid': guid}
            if (bandwidth_limit is not None):
                params['bandwidthLimitInKbps'] = bandwidth_limit
            if (iops_limit is not None):
                params['iops_limit'] = iops_limit
            request = "https://" + server_ip + ":" + server_port + \
                "/api/instances/Volume::" + \
                str(volume_id) + "/action/setMappedSdcLimits"
            LOG.info("set client limit request: %s" % request)
            r = requests.post(
                request,
                data=json.dumps(params),
                headers=headers,
                auth=(
                    server_username,
                    server_token),
                verify=False)
            r = self._check_response(
                r,
                request,
                server_ip,
                server_port,
                server_username,
                server_password,
                server_token,
                False,
                params)
            if (r.status_code != 200):
                response = r.json()
                LOG.info("set client limit response: %s" % response)
                msg = (
                    "Error setting client limits for volume %s: %s" %
                    (volname, response['message']))
                LOG.error(msg)

        return conf

    def disconnect_volume(self, connection_info, disk_info):
        conf = super(LibvirtScaleIOVolumeDriver,
                     self).disconnect_volume(connection_info,
                                             disk_info)
        LOG.info("scaleIO disconnect volume in scaleio libvirt volume driver")
        volname = connection_info['data']['scaleIO_volname']
        sdc_ip = connection_info['data']['hostIP']
        server_ip = connection_info['data']['serverIP']
        server_port = connection_info['data']['serverPort']
        server_username = connection_info['data']['serverUsername']
        server_password = connection_info['data']['serverPassword']
        server_token = connection_info['data']['serverToken']
        LOG.debug(
            "scaleIO Volume name: {0}, SDC IP: {1}, REST Server IP: \
            {2}".format(
                volname,
                sdc_ip,
                server_ip))

        cmd = ['drv_cfg']
        cmd += ["--query_guid"]

        LOG.info("ScaleIO sdc query guid command: " + str(cmd))

        try:
            (out, err) = utils.execute(*cmd, run_as_root=True)
            LOG.info("map volume %s: stdout=%s stderr=%s" % (cmd, out, err))
        except processutils.ProcessExecutionError as e:
            msg = ("Error querying sdc guid: %s" % (e.stderr))
            LOG.error(msg)
            raise exception.NovaException(data=msg)

        guid = out
        msg = ("Current sdc guid: %s" % (guid))
        LOG.info(msg)

        params = {'guid': guid}

        headers = {'content-type': 'application/json'}

        volume_id = self._get_volume_id(
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token,
            volname)
        request = "https://" + server_ip + ":" + server_port + \
            "/api/instances/Volume::" + \
            str(volume_id) + "/action/removeMappedSdc"
        LOG.info("unmap volume request: %s" % request)
        r = requests.post(
            request,
            data=json.dumps(params),
            headers=headers,
            auth=(
                server_username,
                server_token),
            verify=False)
        r = self._check_response(
            r,
            request,
            server_ip,
            server_port,
            server_username,
            server_password,
            server_token,
            False,
            params)

        if (r.status_code != 200):
            response = r.json()
            error_code = response['errorCode']
            if (error_code == 84):
                msg = (
                    "Ignoring error unmapping volume %s: volume not mapped" %
                    (volname))
                LOG.warning(msg)
            else:
                msg = (
                    "Error unmapping volume %s: %s" %
                    (volname, response['message']))
                LOG.error(msg)
                raise exception.NovaException(data=msg)

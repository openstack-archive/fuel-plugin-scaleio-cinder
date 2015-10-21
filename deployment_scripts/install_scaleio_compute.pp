$plugin_settings = hiera('scaleio-cinder')
class {'install_scaleio_compute': }

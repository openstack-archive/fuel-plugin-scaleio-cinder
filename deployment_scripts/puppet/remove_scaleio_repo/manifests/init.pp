# Class: remove_scaleio_repo
#
#
class remove_scaleio_repo {
	# resources

	$files = ['/etc/yum.repos.d/epel.repo','/etc/yum.repos.d/CentOS-Base.repo']

	define remove_repo {
	  file { $name:
		  ensure => absent,
	  }
	}

    remove_repo { $files: }
}
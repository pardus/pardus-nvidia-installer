project('pardus-nvidia-installer',  version: '0.0.1')

# Configuration
gnome = import('gnome')

prefix = get_option('prefix')
sysconfdir = get_option('sysconfdir')
var_dir = get_option('var_dir')
data_dir = join_paths(prefix,get_option('datadir'))
icon_dir = join_paths(prefix,'share','icons','hicolor','scalable','apps')
policy_dir = join_paths(prefix,'share','polkit-1','actions')
pol_auth_dir = join_paths(var_dir,'lib','polkit-1','localauthority','50-local.d')
systemd_service_dir = join_paths(sysconfdir,'systemd','system')

# /usr/share/polkit-1/actions/

desktop_file = 'tr.org.pardus.pardus-nvidia-installer.desktop'
polkit_file = 'tr.org.pardus.pkexec.pardus-nvidia-installer.policy'
pkla_file = 'pardus-nvidia-installer-group.pkla'
desktop_file_dir = join_paths(prefix,'share','applications')

# Source files
source_dir = join_paths(prefix , 'share' , 'pardus' , 'pardus-nvidia-installer')
install_data([desktop_file],install_dir : desktop_file_dir)
install_data(['pardus-nvidia-installer.svg'],install_dir:icon_dir)
install_data(['pardus-nvidia-installer','pardus-nvidia-installer.svg'], install_dir : source_dir)
install_data([polkit_file],install_dir : policy_dir)
install_data([pkla_file],install_dir:pol_auth_dir)
install_data('pni-disable-gpu.service', systemd_service_dir)
install_data(['pni-disable-gpu.sh'], install_dir : source_dir)

install_subdir('data',install_dir : source_dir)
install_subdir('src',install_dir : source_dir)
install_subdir('ui',install_dir : source_dir)

install_data(['pardus-nvidia-installer'], install_dir : prefix / 'bin')

# locale settings
subdir('data/po')


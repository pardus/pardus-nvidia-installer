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
# /usr/share/polkit-1/actions/

desktop_file = 'tr.org.pardus.pardus-nvidia-installer.desktop'
polkit_file = 'tr.org.pardus.pkexec.pardus-nvidia-installer.policy'
pkla_file = 'pardus-nvidia-installer-group.pkla'
desktop_file_dir = join_paths(prefix,'share','applications')
service_file = 'pni-disable-gpu.service'
service_runner = 'pni-disable-gpu.sh'
update_translation_file = 'update_translations.sh'
nvidia_gpg = 'nvidia-drivers.gpg'
nvidia_list = 'nvidia-drivers.list'
nvidia_pub = 'nvidia.pub'
# Source files
source_dir = join_paths(prefix , 'share' , 'pardus' , 'pardus-nvidia-installer')
install_data([desktop_file],install_dir : desktop_file_dir)
install_data(['pardus-nvidia-installer.svg'],install_dir:icon_dir)
install_data(['pardus-nvidia-installer','pardus-nvidia-installer.svg'], install_dir : source_dir)
install_data([polkit_file],install_dir : policy_dir)
install_data([pkla_file],install_dir:pol_auth_dir)
install_data([service_runner, update_translation_file], install_dir : source_dir, install_mode : 'rwxr--r--')
install_data([service_file], install_dir : '/lib/systemd/system/', install_mode : 'rw-r--r--')

install_subdir('data',install_dir : source_dir)
install_subdir('src',install_dir : source_dir)
install_subdir('ui',install_dir : source_dir)

install_data(['pardus-nvidia-installer'], install_dir : prefix / 'bin')
install_data([nvidia_gpg,nvidia_list, nvidia_pub], install_dir :source_dir)

# locale settings
subdir('data/po')


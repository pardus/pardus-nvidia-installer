project('pardus-nvidia-installer',  version: '0.0.1')

# Configuration
gnome = import('gnome')

prefix = get_option('prefix')
sysconfdir = get_option('sysconfdir')

data_dir = join_paths(prefix,get_option('datadir'))
icon_dir = join_paths(prefix,'share','icons','hicolor','scalable','apps')
desktop_file = 'tr.org.pardus.pardus-gnome-greeter.desktop'

desktop_file_dir = join_paths(prefix,'share','applications')

# Source files
source_dir = join_paths(prefix , 'share' , 'pardus' , 'pardus-nvidia-installer')
install_data([desktop_file],install_dir : desktop_file_dir)
install_data(['pardus-nvidia-installer.svg'],install_dir:icon_dir)
install_data(['pardus-nvidia-installer','pardus-nvidia-installer.svg'], install_dir : source_dir)
install_data([desktop_file],install_dir : auto_start_dir)

install_subdir('data',install_dir : source_dir)
install_subdir('src',install_dir : source_dir)
install_subdir('ui',install_dir : source_dir)

install_data(['pardus-gnome-greeter'], install_dir : prefix / 'bin')

# locale settings
# subdir('data/po')


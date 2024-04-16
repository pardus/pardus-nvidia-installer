## Pardus Nvidia Installer

Installing Nvidia GPU drivers for Pardus with few clicks.

### Installation

#### Tech Stack: `Python`, `GTK3`

#### Programming Logic
* Nvidia devices and their available drivers are stored in `data/nvidia-pci.json` files
* Application scan whole system devices and gets nvidia devices only. 
* After filtered nvidia devices, each nvidia devices is checked for available drivers from yaml file.
* Installation is pretty straight forward. Select driver and click `Apply Changes` button.
* After installation is done, you need to reboot your system. And your new driver is ready to use.

### TODO
- [x] Parsing json file to make it easy to use with application.
- [x] Scanning whole system pci devices and finding Nvidia devices.
- [x] Filtering Nvidia drivers for Nvidia devices.
- [x] Creating user interface depends on the scenario. 
- [x] Adding prompt for rebooting system after installation. 
- [x] Creating policies and implementing it with GTK.
- [x] Multiple device and driver support.
- [x] Adding about dialog for application.
- [x] Adding a logo for application.

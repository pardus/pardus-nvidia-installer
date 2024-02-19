#!/bin/bash
set -ex
if [[ ! -f /var/cache/pni-disable-gpu ]] &>/dev/null; then
    exit 0
fi
if grep "nomodeset" /proc/cmdline ; then
    exit 0
fi

remove_pci(){
    if [[ -d "/sys/bus/pci/devices/$1/driver" ]] ; then
        module=$(basename $(readlink /sys/bus/pci/devices/$1/driver/module))
        echo "Disabled: $module ($1)"
        rmmod -f $module
    fi
    echo 1 > /sys/bus/pci/devices/$1/remove
}

echo 1 > /sys/bus/pci/rescan
ls /sys/class/drm/card[0-9*]
for dir in  $(ls /sys/bus/pci/devices/); do
    # 03 Display controlleretc
    # 02 3D controller
    if grep "^0x0302" /sys/bus/pci/devices/$dir/class ; then
      pci="$dir"
      echo "Found 3D controller: ${pci:5}"
      remove_pci "$pci"
    fi
done
udevadm control --reload


#!/bin/bash
set -ex
if [[ ! -f /var/cache/pni-disable-gpu ]]; then
    exit 0
fi
if grep -q "nomodeset" /proc/cmdline ; then
    exit 0
fi

remove_pci(){
    if [[ -d "/sys/bus/pci/devices/$1/driver" ]] ; then
        module=$(basename $(readlink /sys/bus/pci/devices/$1/driver/module))
        echo "Disabled: $module ($1)"
        rmmod -f $module || true
    fi
    echo 1 > /sys/bus/pci/devices/$1/remove || true
}
 
has_primary=0
for d in /sys/bus/pci/devices/*/boot_vga; do
    [ -r "$d" ] && [ "$(cat "$d" 2>/dev/null)" = "1" ] && { has_primary=1; break; }
done
if [ "$has_primary" != "1" ]; then
    echo "No boot_vga=1 primary identified; refusing to remove GPUs."
    exit 0
fi

for dir in $(ls /sys/bus/pci/devices/); do
    # Only Nvidia devices
    vendor=$(cat /sys/bus/pci/devices/$dir/vendor 2>/dev/null || true)
    [ "$vendor" = "0x10de" ] || continue
    # Only display controller functions (class 0x03xxxx): VGA (0300),
    # 3D (0302), other (0380). Skips the card's audio/USB/bridge functions.
    class=$(cat /sys/bus/pci/devices/$dir/class 2>/dev/null || true)
    case "$class" in
        0x03*) ;;
        *) continue ;;
    esac
    # Never remove the card the firmware booted the display on. The kernel
    # exposes boot_vga only for the VGA-class boot device; "1" means primary.
    boot_vga=$(cat /sys/bus/pci/devices/$dir/boot_vga 2>/dev/null || true)
    if [ "$boot_vga" = "1" ]; then
        echo "Skipping boot display device: $dir"
        continue
    fi
    echo "Found secondary GPU: $dir"
    remove_pci "$dir"
done
udevadm settle --timeout=30

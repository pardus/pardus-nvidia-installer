# Pardus Nvidia Installer

## Introduction

Pardus Nvidia Installer is a graphical tool that helps you install and manage NVIDIA GPU drivers on Pardus. 
It detects your hardware, shows the drivers that fit it, and installs your choice with a single click — no terminal, no guesswork.

## Features

* User-friendly interface
* Automatic detection of NVIDIA GPUs
* Suggests only the drivers that match your hardware
* Open-source `nouveau` driver as a fallback
* Optional NVIDIA CUDA repository for newer driver versions
* Disable/enable a secondary (discrete) GPU on hybrid laptops
* Safe by design: the primary display GPU is never removed
* Reboot prompt after changes that need one

## Installation

### Requirements

Before running Pardus Nvidia Installer, make sure your system has:

* `python3`: The application is built with Python 3.
* `python3-gi`: Lets Python use GTK and GNOME libraries.
* `gir1.2-gtk-3.0`: The GTK 3 graphical toolkit.
* `gir1.2-vte-2.91`: Embedded terminal used to show installation progress.
* `gir1.2-polkit-1.0`: PolicyKit integration for privileged actions.
* `python3-apt`: Used to query and install driver packages.
* `pciutils`: Provides the PCI device database (`/usr/share/misc/pci.ids`).
* `gnupg`: Verifies the NVIDIA repository signing key.

### Usage

* **From Package Manager**

```
sudo apt install pardus-nvidia-installer
```

* **From Source**

```
# Clone the repository
git clone https://github.com/pardus/pardus-nvidia-installer
# Navigate to the project directory
cd pardus-nvidia-installer
# Install dependencies
sudo apt install python3 python3-gi gir1.2-gtk-3.0 gir1.2-vte-2.91 \
    gir1.2-polkit-1.0 python3-apt pciutils gnupg
# Run the application
python3 src/Main.py
```

## Usage Guide

1. Launch the application. It scans your system and lists the NVIDIA GPUs it finds.
2. Pick a driver for your card (or choose the open-source `nouveau` driver).
3. Click **Apply Changes** and authenticate when prompted.
4. Watch the progress in the built-in terminal.
5. Reboot when asked, so the new driver loads.

### Extra options

* **NVIDIA repository:** Turn on the switch to add NVIDIA's CUDA repository and get newer driver versions.
* **Disable secondary GPU:** On hybrid (Optimus) machines, disable the discrete NVIDIA card to save power. The card is removed at boot, while your primary display always stays active.

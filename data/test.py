#!/usr/bin/env python3
import json

json_files = ["current.json", "470.json", "390.json", "340.json"]
drivers = [
    "nvidia-driver",
    "nvidia-tesla-470-driver",
    "nvidia-legacy-390xx-driver",
    "nvidia-legacy-340xx-driver",
]

w = open("output.json", "a")
obj = {}
for index, item in enumerate(json_files):
    f = open(item, "r")
    datas = json.loads(f.read())
    obj[drivers[index]] = {}
    for data in datas:
        obj[drivers[index]][data["pci"]] = data["name"]

w.write(json.dumps(obj))

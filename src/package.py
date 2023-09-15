import apt

cache = apt.Cache()


def get_pkg_info(package_name: str):
    pkg = cache[package_name]
    if pkg.is_installed:
        version = pkg.installed.version
        name = pkg.installed.raw_description
    else:
        version = pkg.versions[0].version
        name = pkg.versions[0].raw_description

    return {"ver": version, "name": name}

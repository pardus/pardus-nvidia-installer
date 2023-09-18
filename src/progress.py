import apt
import os
from apt.progress.base import AcquireProgress, InstallProgress

apt_pkg.init_config()
apt_pkg.config.set("DPkg::Options::", "--force-confnew")
apt_pkg.config.set("APT::Get::Assume-Yes", "true")
apt_pkg.config.set("APT::Get::force-yes", "true")
# TODO fix this
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
os.environ["DEBONF_NONINTERACTIVE_SEEN"] = "true"
# ...


class CustomAcquireProgress(AcquireProgress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def fetch(self, item):
        self._item = item
        super().fetch(item)

    def pulse(self, owner):
        if hasattr(self, "_item"):
            self.total_percentage = self.current_bytes / self.total_bytes * 100
            print(f"İndiriliyor {self._item.shortdesc}: %{self.total_percentage:.2f}")
        return super().pulse(owner)

    def done(self, item):
        if hasattr(self, "_item"):
            print(f"Download done: {self._item.shortdesc}")

    def fail(self, item):
        if hasattr(self, "_item"):
            print(f"Fail to download: {self._item.shortdesc}")


class CustomInstallProgress(InstallProgress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def error(self, pkg, errormsg):
        print(f"Hata: {pkg} paketi kurulamadı: {errormsg}")

    def status_change(self, pkg, percent, status):
        print(f"pkg:{pkg} -- percent:{percent} -- status:{status}")

    def finish_update(self):
        print("Kurulum tamamlandı.")


def install_package(package_names):
    cache = apt.Cache()
    # cache.update()
    cache.open()

    for package_name in package_names:
        if not cache[package_name].is_installed:
            print(f"{package_name} paketi kurulacak...")
            package = cache[package_name]
            package.mark_install()

    try:
        acquire_progress = CustomAcquireProgress()
        install_progress = CustomInstallProgress()
        cache.commit(acquire_progress, install_progress)
        print(f"{package_name} paketi başarıyla kuruldu.")

    except Exception as e:
        print(f"{package_name} paketi kurulamadı. Hata: {str(e)}")


if __name__ == "__main__":
    package_names = ["pardus-software"]  # Paket adını buraya girin
    install_package(package_names)

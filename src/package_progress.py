import apt
import apt_pkg
import os
from states import pkg_ins_progress
from apt.progress.base import AcquireProgress, InstallProgress

apt_pkg.init_config()
apt_pkg.config.set("DPkg::Options::", "--force-confnew")
apt_pkg.config.set("APT::Get::Assume-Yes", "true")
apt_pkg.config.set("APT::Get::force-yes", "true")
# TODO fix this
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
os.environ["DEBONF_NONINTERACTIVE_SEEN"] = "true"
# ...
print("pkg prs value: ", pkg_ins_progress.value)


class CustomAcquireProgress(AcquireProgress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def fetch(self, item):
        self._item = item
        super().fetch(item)

    def pulse(self, owner):
        if hasattr(self, "_item"):
            self.total_percentage = self.current_bytes / self.total_bytes * 100
            pkg_ins_progress.value = self.total_percentage
            # print(f"İndiriliyor {self._item.shortdesc}: %{self.total_percentage:.2f}")
        return super().pulse(owner)

    def done(self, item):
        if hasattr(self, "_item"):
            # print(f"Download done: {self._item.shortdesc}")
            pass

    def fail(self, item):
        if hasattr(self, "_item"):
            # print(f"Fail to download: {self._item.shortdesc}")
            pass


class CustomInstallProgress(InstallProgress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def error(self, pkg, errormsg):
        print(f"Hata: {pkg} paketi kurulamadı: {errormsg}")

    def status_change(self, pkg, percent, status):
        pkg_ins_progress.value = percent
        print(f"pkg:{pkg} -- percent:{percent} -- status:{status}")

    def finish_update(self):
        print("Kurulum tamamlandı.")

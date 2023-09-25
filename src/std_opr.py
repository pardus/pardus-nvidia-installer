import gi
from gi.repository import GLib, Gio


def on_process_stdout(src, cond, prg_bar,last_param):

    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    print(line)
    #prog_txt = ""
    if "dlstatus"  in line or  "pmstatus" in line:
        splits = line.split(":")
        prc = float(splits[2])
        txt = splits[3]      
        prg_frac = float(prc / 100)
        prog_txt = f"Status %{prc:.2f} :: {txt}"
        prg_bar.set_text(prog_txt)
        prg_bar.set_fraction(prg_frac)
    return True


def on_process_stderr(src, cond, ui_obj):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    return True


def on_process_stdext(pid, stat, ui_obj):
    ui_obj.set_fraction(1)
    if stat == 0:
        ui_obj.set_text("Selected driver installed successfully.")

    else:
        ui_obj.set_text("An error occured during installation.")
    return True

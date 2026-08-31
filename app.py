import ctypes
from ctypes import wintypes
import os
import base64
import sys
import threading
import time
import configparser
import webview
import tkinter as tk
from tkinter import filedialog



if sys.platform=="win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.example.AudioEditorAppp")


def resource_path(p):
    try:b=sys._MEIPASS
    except:b=os.path.abspath(".")
    return os.path.join(b,p)

data_dir=os.path.join(os.path.expanduser("~"),".AudioEditor")
os.makedirs(data_dir,exist_ok=True)
CONFIG_FILE=os.path.join(data_dir,"config.ini")

WINDOW_TITLE = "Audio Editor"

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


class Api:
    def save_export(self, base64_data, filename):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        ext = os.path.splitext(filename)[1].lower()

        filetypes = {
            ".mp3": [("MP3 Audio", "*.mp3")],
            ".wav": [("WAV Audio", "*.wav")],
            ".aac": [("AAC Audio", "*.aac")],
            ".ogg": [("OGG Audio", "*.ogg")],
            ".flac": [("FLAC Audio", "*.flac")]
        }.get(ext, [("All Audio Files", "*.*")])

        file_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=filetypes,
            initialfile=filename,
            title="Save Audio As"
        )

        root.destroy()

        if not file_path:
            return "cancel"

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))

        return "success"

class Icon:
    def __init__(self,title,path):
        self.title=title
        self.path=os.path.abspath(path) if path else None

    def find(self):
        hwnd=self.user32.FindWindowW(None,self.title)
        if hwnd:return hwnd
        found=[]
        @ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        def cb(hwnd,_):
            n=self.user32.GetWindowTextLengthW(hwnd)+1
            b=ctypes.create_unicode_buffer(n)
            self.user32.GetWindowTextW(hwnd,b,n)
            if self.title in b.value:found.append(hwnd)
            return True
        self.user32.EnumWindows(cb,0)
        return found[0] if found else None

    @property
    def user32(self):return ctypes.windll.user32

    def set(self):
        if not self.path or not os.path.exists(self.path):return
        hwnd=None
        for _ in range(50):
            if hwnd:=self.find():break
            time.sleep(.1)
        if not hwnd:return
        try:
            for size,msg in ((16,0),(32,1)):
                icon=self.user32.LoadImageW(0,self.path,1,size,size,0x10)
                if icon:self.user32.SendMessageW(hwnd,0x80,msg,icon)
        except:pass


def rgb(r, g, b):
    return r | (g << 8) | (b << 16)


def set_titlebar_color(hwnd):
    bg = ctypes.c_int(rgb(7, 16, 37))
    fg = ctypes.c_int(rgb(255, 255, 255))

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_CAPTION_COLOR,
        ctypes.byref(bg),
        ctypes.sizeof(bg)
    )

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_TEXT_COLOR,
        ctypes.byref(fg),
        ctypes.sizeof(fg)
    )

    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_BORDER_COLOR,
        ctypes.byref(bg),
        ctypes.sizeof(bg)
    )

def load_config():
    d={"x":None,"y":None,"width":1000,"height":700,"fullscreen":False}
    try:
        c=configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):return d
        c.read(CONFIG_FILE,encoding="utf-8")
        if "Window" not in c:return d
        s=c["Window"]
        d["x"]=None if s.get("x","None").lower()=="none" else int(s["x"])
        d["y"]=None if s.get("y","None").lower()=="none" else int(s["y"])
        d["width"]=s.getint("width",fallback=1000)
        d["height"]=s.getint("height",fallback=700)
        d["fullscreen"]=s.getboolean("fullscreen",fallback=False)
    except:pass
    return d

def save_config(w):
    try:
        c=configparser.ConfigParser()
        c["Window"]={
            "x":str(w.x),"y":str(w.y),"width":str(w.width),
            "height":str(w.height),"fullscreen":str(w.fullscreen).lower()
        }
        with open(CONFIG_FILE,"w",encoding="utf-8") as f:c.write(f)
    except:pass
    

def wait_for_window(window, fullscreen):
    hwnd = 0

    while hwnd == 0:
        hwnd = user32.FindWindowW(None, WINDOW_TITLE)
        time.sleep(0.05)

    set_titlebar_color(hwnd)

    if fullscreen:
        time.sleep(0.2)
        window.toggle_fullscreen()


# Load saved settings
settings = load_config()
user32=ctypes.windll.user32
dwmapi=ctypes.windll.dwmapi
title_bar = 7 | (16 << 8) | (37 << 16)
WHITE=255|(255<<8)|(255<<16)

def titlebar():
    while not (hwnd:=user32.FindWindowW(None,"PDF Text Editor")):time.sleep(.05)
    for attr,color in ((35,title_bar),(36,WHITE),(34,title_bar)):
        v=ctypes.c_int(color)
        dwmapi.DwmSetWindowAttribute(hwnd,attr,ctypes.byref(v),ctypes.sizeof(v))


# Read HTML
with open(r"assets/index.html", "r", encoding="utf-8") as f:
    html = f.read()

html_path=resource_path("assets/index.html")
# Create window
args={
    "title":"PDF Text Editor",
    "url":html_path,
    "width":settings["width"],
    "height":settings["height"],
    "fullscreen":settings["fullscreen"],
    "js_api":Api()
}
if settings["x"] is not None:args["x"]=settings["x"]
if settings["y"] is not None:args["y"]=settings["y"]

window=webview.create_window(**args)

# Save geometry before the window closes
window.events.closing += lambda: save_config(window)

# Apply titlebar color and restore fullscreen state
threading.Thread(
    target=wait_for_window,
    args=(window, settings["fullscreen"]),
    daemon=True
).start()
threading.Thread(target=titlebar,daemon=True).start()
icon=Icon("PDF Text Editor",resource_path(r"assets\icon.ico"))
threading.Thread(target=lambda:(time.sleep(1),icon.set()),daemon=True).start()

webview.start()

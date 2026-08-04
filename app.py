import os
os.environ["PATH"] += os.pathsep + r"H:\My Drive\MODELS\ffmpeg\bin"
import ctypes
import time
import webview
import tempfile
from pathlib import Path
import sys
from pydub import AudioSegment
import base64
from tkinter import filedialog
import threading
import signal
from ctypes import wintypes


def resource_path(relative_path):
    """Get absolute path to resource (for PyInstaller compatibility)"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class WindowIconSetter:
    def __init__(self, window_title, icon_path):
        self.window_title = window_title
        self.icon_path = os.path.abspath(icon_path) if icon_path else None
        
        # Windows API
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        
    def find_window_by_title(self, title):
        """Find window by title with partial matching"""
        hwnd = self.user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
        
        # If exact match fails, try to enumerate all windows
        windows = []
        
        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_windows_callback(hwnd, lParam):
            length = self.user32.GetWindowTextLengthW(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            self.user32.GetWindowTextW(hwnd, buffer, length)
            
            if title in buffer.value:
                windows.append(hwnd)
            return True
        
        self.user32.EnumWindows(enum_windows_callback, 0)
        
        if windows:
            return windows[0]
        
        return None
    
    def set_icon(self):
        """Set icon for the window"""
        if not self.icon_path or not os.path.exists(self.icon_path):
            print(f"Icon file not found: {self.icon_path}")
            return False
        
        # Find window
        hwnd = None
        for i in range(50):  # Try for 5 seconds
            hwnd = self.find_window_by_title(self.window_title)
            if hwnd:
                break
            time.sleep(0.1)
        
        if not hwnd:
            print(f"Window '{self.window_title}' not found")
            return False
        
        # Load and set icon
        try:
            # Load icon from file
            LR_LOADFROMFILE = 0x10
            IMAGE_ICON = 1
            
            # Small icon (16x16)
            hicon_small = self.user32.LoadImageW(
                0,
                self.icon_path,
                IMAGE_ICON,
                16, 16,
                LR_LOADFROMFILE
            )
            
            # Large icon (32x32)
            hicon_large = self.user32.LoadImageW(
                0,
                self.icon_path,
                IMAGE_ICON,
                32, 32,
                LR_LOADFROMFILE
            )
            
            # Set icons
            WM_SETICON = 0x80
            ICON_SMALL = 0
            ICON_BIG = 1
            
            if hicon_small:
                self.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            
            if hicon_large:
                self.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_large)
            
            
            # print(f"Icon set successfully for window '{self.window_title}'")
            return True
            
        except Exception as e:
            print(f"Error setting icon: {e}")
            return False

class Api:
    def __init__(self):
        self.current_audio_path = None
        self.window = None
        self.export_cancelled = False
        self.current_export_path = None
        self._lock = threading.Lock()

    def set_window(self, window):
        self.window = window

    def set_current_audio(self, audio_path):
        self.current_audio_path = audio_path
        return True

    def cancel_export(self):
        """Cancel current export process."""
        self.export_cancelled = True
        if self.current_export_path and os.path.exists(self.current_export_path):
            try:
                os.remove(self.current_export_path)
                print(f"Cancelled export and removed: {self.current_export_path}")
            except Exception as e:
                print(f"Error removing cancelled export file: {e}")
        return True

    def export_audio(self, format_type, speed_rate=1.0):
        """Export the current audio with selected format and speed."""
        self.export_cancelled = False
        self.current_export_path = None

        try:
            if not self.current_audio_path or not os.path.exists(self.current_audio_path):
                return {"success": False, "error": "No audio file loaded"}

            original_path = Path(self.current_audio_path)
            default_filename = f"{original_path.stem}_{speed_rate}x.{format_type}"

            export_path = filedialog.asksaveasfilename(
                defaultextension=f".{format_type}",
                initialfile=default_filename,
                filetypes=[(format_type.upper(), f"*.{format_type}")]
            )

            if not export_path:
                return {"success": False, "error": "Export cancelled"}

            if self.export_cancelled:
                return {"success": False, "error": "Export cancelled"}

            audio = AudioSegment.from_file(self.current_audio_path)

            if self.export_cancelled:
                return {"success": False, "error": "Export cancelled"}

            # Adjust speed if needed
            if speed_rate != 1.0:
                new_frame_rate = int(audio.frame_rate * speed_rate)
                audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
                audio = audio.set_frame_rate(audio.frame_rate)

            if self.export_cancelled:
                return {"success": False, "error": "Export cancelled"}

            self.current_export_path = export_path

            # Export to selected format
            if format_type == "mp3":
                audio.export(export_path, format="mp3", bitrate="192k")
            elif format_type == "wav":
                audio.export(export_path, format="wav")
            elif format_type == "aac":
                audio.export(export_path, format="adts")
            elif format_type == "ogg":
                audio.export(export_path, format="ogg")
            elif format_type == "flac":
                audio.export(export_path, format="flac")
            else:
                return {"success": False, "error": f"Unsupported format: {format_type}"}

            if self.export_cancelled and os.path.exists(export_path):
                os.remove(export_path)
                return {"success": False, "error": "Export cancelled"}

            return {
                "success": True,
                "message": f"Audio exported successfully as {format_type.upper()} with {speed_rate}x speed",
                "file_path": export_path
            }

        except Exception as e:
            if self.current_export_path and os.path.exists(self.current_export_path):
                try:
                    os.remove(self.current_export_path)
                except:
                    pass
            return {"success": False, "error": str(e)}

        finally:
            self.current_export_path = None

    def save_audio_file(self, audio_data, filename):
        """Save a base64-encoded audio file to a temp directory."""
        try:
            if audio_data.startswith('data:audio'):
                audio_data = audio_data.split(',')[1]
            audio_bytes = base64.b64decode(audio_data)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, filename)

            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            self.current_audio_path = temp_path
            return {"success": True, "path": temp_path}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_all_processes(self):
        """Gracefully stop any ongoing processes."""
        with self._lock:
            self.export_cancelled = True
            # print("🛑 Stopping all processes and closing the app...")
            print("Stopping all processes and closing the app...")
            if self.current_export_path and os.path.exists(self.current_export_path):
                try:
                    os.remove(self.current_export_path)
                    print(f"Removed temporary export file: {self.current_export_path}")
                except Exception as e:
                    print(f"Error removing file: {e}")
            os._exit(0)  # Immediate stop of all threads and processes

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def rgb(r, g, b):
    # Windows COLORREF (0x00BBGGRR)
    return r | (g << 8) | (b << 16)


def set_titlebar_red(hwnd):
    red = ctypes.c_int(rgb(7,16,37))
    white = ctypes.c_int(rgb(255, 255, 255))

    # Red caption
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_CAPTION_COLOR,
        ctypes.byref(red),
        ctypes.sizeof(red),
    )

    # White title text
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_TEXT_COLOR,
        ctypes.byref(white),
        ctypes.sizeof(white),
    )

    # Red border
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_BORDER_COLOR,
        ctypes.byref(red),
        ctypes.sizeof(red),
    )


def wait_and_color():
    title = "🎵 Audio Editor"

    hwnd = 0

    while hwnd == 0:
        hwnd = user32.FindWindowW(None, title)
        time.sleep(0.05)

    print("HWND:", hwnd)

    set_titlebar_red(hwnd)


def create_window():
    html_file = resource_path("assets/index.html")
    api = Api()
    window = webview.create_window(
        "🎵 Audio Editor",
        f"file://{html_file}",
        width=1000,
        height=650,
        resizable=True,
        js_api=api,
        
    )
    api.set_window(window)
    return window, api


if __name__ == '__main__':
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Installing pydub and ffmpeg dependencies...")
        os.system(f"{sys.executable} -m pip install pydub")

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.example.AudioEditorApp")
    
    

    # Apply .ico window icon
    icon_path = resource_path(r"assets\icon.ico")  # (make sure icon.ico exists)
    icon_setter = WindowIconSetter("🎵 Audio Editor", icon_path)

    def apply_icon_async(): 
        time.sleep(1)
        icon_setter.set_icon()

    threading.Thread(target=apply_icon_async, daemon=True).start()

    window, api = create_window()
    # Add shutdown handler for window close
    def on_close():
        api.stop_all_processes()

    window.events.closing += on_close

    # Ctrl+C / SIGINT handler
    def handle_exit(signum, frame):
        api.stop_all_processes()

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    threading.Thread(target=wait_and_color, daemon=True).start()
    webview.start()

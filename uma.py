# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import tkframe

import PIL.Image
import PIL.ImageGrab, PIL.ImageOps

import win32gui, win32con
import ctypes

import math

import viewrecognizer

import logging

#---
class FrameTargetWindow(tkframe.BaseFrame):
    """対象ウィンドウハンドルの処理"""
    def init_variables(self):
        self.hwnd = tk.IntVar()
        self.onclick_acquire_target_window()

    def init_widgets(self):
        self.set_inside_layout('grid')
        self.add_widget(ttk.Label(self, text = "Window"), row = 0, column = 0)
        self.add_widget(ttk.Entry(self, textvariable = self.hwnd, state = 'readonly'), row = 0, column = 1, columnspan = 2, padx = 4)
        self.add_widget(ttk.Button(self, text = "acquire", command = self.onclick_acquire_target_window), row = 0, column = 3)

    def onclick_acquire_target_window(self):
        """キャプションからウィンドウIDの取得"""
        hwnd = win32gui.FindWindow("UnityWndClass", "umamusume")
        self.hwnd.set(hwnd)

class FrameScenarioEvent(tkframe.BaseFrame):
    """イベント取得"""
    def __init__(self, parent, assocdata, **kwargs):
        super().__init__(parent, assocdata, **kwargs)

        if not 'hwnd' in assocdata: raise KeyError("Widget must be specified for 'hwnd' data.") #TODO: この辺りの処理を一般化したい

        try:
            self.OCR = viewrecognizer.UmaAdvChoiceRecognizer()
        except Exception as err:
            messagebox.showerror("error", str(err))

    def init_variables(self):
        self.title = tk.StringVar()
        self.title.set("未取得")
        self.info = tk.StringVar()
        self.info.set("[未取得]")

    def init_widgets(self):
        self.set_inside_layout('pack')
        self.add_widget(ttk.Button(self, text = "Go", command = self.onclick_display_event_info), side = tk.TOP, anchor = tk.W, pady = 8)
        self.add_widget(ttk.Label(self, text = "イベント:"), side = tk.TOP, anchor = tk.W, pady = 4)
        self.add_widget(ttk.Label(self, textvariable = self.title, relief = 'groove'), side = tk.TOP, anchor = tk.W, padx = 8)
        self.add_widget(ttk.Label(self, text = "選択肢:"), side = tk.TOP, anchor = tk.W, pady = 8)
        self.add_widget(ttk.Label(self, textvariable = self.info, relief = 'groove'), side = tk.TOP, anchor = tk.W, expand = 1, fill = tk.X, padx = 8)

        # 試験用
        self.add_widget(ttk.Button(self, text = "test", command = self.onclick_display_event_info_test), side = tk.RIGHT, anchor = tk.SE)
        self.add_widget(ttk.Button(self, text = "capture", command = self.onclick_capture_test), side = tk.RIGHT, anchor = tk.SE)

    #---
    def onclick_display_event_info(self):
        uhwfunc = self.get_associated_data('update_hwnd_func')
        if uhwfunc: uhwfunc()
        hwnd = int(self.get_associated_data('hwnd'))
        try:
            image = capture_window(hwnd)
        except Exception as err:
            messagebox.showerror("error", str(err))
            return

        ttl, sel = self.OCR.OCR_event_view(image)
        event = self.OCR.find_event_info(ttl, sel)
        self.display_event_info(event)

    def onclick_capture_test(self):
        uhwfunc = self.get_associated_data('update_hwnd_func')
        if uhwfunc: uhwfunc()
        hwnd = int(self.get_associated_data('hwnd'))
        image = capture_window(hwnd)
        image.save("sstest.png")

    def onclick_display_event_info_test(self): 
        image = PIL.Image.open("sstest.png")

        ttl, sel = self.OCR.OCR_event_view(image)
        event = self.OCR.find_event_info(ttl, sel)
        
        self.display_event_info(event)

    def display_event_info(self, event):
        # UIに出力
        if not event:
            self.title.set("* not found *")
            self.info.set("* not found *")
            return
        self.title.set("[%s]\n%s" % (event[1], event[0]))
        self.info.set("\n".join(map(lambda s: "■%s\n%s\n" % s, event[2])))

def capture_window(hwnd):
    """枠を除いてクライアント領域をキャプチャする"""
    wrect = win32gui.GetWindowRect(hwnd)
    csize = win32gui.GetClientRect(hwnd)
    bs = (wrect[2] - wrect[0] - csize[2]) // 2
    ts = (wrect[3] - wrect[1] - csize[3] - bs)
    crect = (wrect[0] + bs, wrect[1] + ts, wrect[2] - bs, wrect[3] - bs)
    return PIL.ImageGrab.grab(crect)

class FrameWindowRect(tkframe.BaseFrame):
    """ウィンドウサイズ変更
     対象のアプリが管理者権限で起動するため、こちらも特権が必要になることに注意
    """
    def __init__(self, parent, assocdata, **kwargs):
        super().__init__(parent, assocdata, **kwargs)

        if not 'hwnd' in assocdata: raise KeyError("Widget must be specified for 'hwnd' data.")

    def init_variables(self):
        self.width = tk.IntVar()
        self.height = tk.IntVar()
        self.onclick_acquire_target_window()

    def init_widgets(self):
        #state = tk.NORMAL if self.check_privileged() else tk.DISABLED
        if self.check_privileged():
            self.set_inside_layout('pack')
            self.add_widget(ttk.Label(self, text = "Window Size"), side = tk.TOP, anchor = tk.NW, pady = 4)
            self.add_widget(ttk.Entry(self, textvariable = self.width, width = 8),side = tk.LEFT, anchor = tk.W, padx = 4)
            self.add_widget(ttk.Label(self, text = "x"), side = tk.LEFT, anchor = tk.W)
            self.add_widget(ttk.Entry(self, textvariable = self.height, width = 8), side = tk.LEFT, anchor = tk.W, padx = 4)
            self.add_widget(ttk.Button(self, text = "set", command = self.onclick_set_window_size), side = tk.LEFT, anchor = tk.W, padx = (8, 0))

    #---
    def check_privileged(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def onclick_acquire_target_window(self):
        hwnd = int(self.get_associated_data('hwnd'))
        if not hwnd: return

        csize = win32gui.GetClientRect(hwnd)
        self.width.set(csize[2])
        self.height.set(csize[3])

    def onclick_set_window_size(self):
        self.onchange_width() #TODO: traceで数値変更時に呼ぶようにしたい
        hwnd = int(self.get_associated_data('hwnd'))
        if not hwnd: return

        wid = int(self.width.get())
        hgt = int(self.height.get())
        if wid <= 0 or hgt <= 0: return

        wrect = win32gui.GetWindowRect(hwnd)
        csize = win32gui.GetClientRect(hwnd)
        nw = (wrect[2] - wrect[0] - csize[2]) + wid;
        nh = (wrect[3] - wrect[1] - csize[3]) + hgt;
        win32gui.SetWindowPos(hwnd, None, 0, 0, nw, nh, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER);

    def onchange_width(self):
        wid = int(self.width.get())
        self.height.set(math.ceil((852 * wid) / 480))

#---
def main():
    logging.basicConfig(level = logging.INFO)

    root = tk.Tk()
    root.title("ウマ選択肢チェッカー")

    frame_tgt = FrameTargetWindow(root, padding = 16, relief='flat')
    ap = {'hwnd': frame_tgt.hwnd, 'update_hwnd_func': frame_tgt.onclick_acquire_target_window} #TODO: ここにコールバック関数を混ぜるのは綺麗でないので何か考える
    frame_ocr = FrameScenarioEvent(root, ap, padding = 16, relief='ridge')
    frame_wrt = FrameWindowRect(root, ap, padding = 16, relief='flat')

    frame_tgt.layout(anchor = tk.W)
    frame_ocr.layout(anchor = tk.W, fill = tk.X)
    frame_wrt.layout(anchor = tk.W)

    #
    root.mainloop()


#----
if __name__ == "__main__":
    main()

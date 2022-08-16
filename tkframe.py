# -*- coding: utf-8 -*-
"""
 GUI(TkのFrame)用のベースクラス
"""
import tkinter as tk
from tkinter import ttk

#---
class BaseFrame(ttk.Frame):
    """Base Tk.Frame class"""
    geometry_managers = ('pack', 'grid', 'place')
    
    def __init__(self, parent = None, assocdata = None, **kwargs):
        """assocdata: フレーム外にあるUI(のデータ)を参照する辞書"""
        super().__init__(parent, **kwargs)
        
        self.widgets = []
        self.layout_inside = 'pack'
        self.associated_data = assocdata.copy() if assocdata else None
        self.init_variables()
        self.init_widgets()

    def add_widget(self, wobj, **pack_args):
        self.widgets.append((wobj, pack_args))
    
    def set_inside_layout(self, name):
        BaseFrame.check_geometry_manager_name(name)
        self.layout_inside = name
    @classmethod
    def check_geometry_manager_name(cls, name):
        if name not in cls.geometry_managers:
            raise AttributeError("Layout manager must be specified with " + "/".join(cls.geometry_managers))

    def layout(self, method = 'pack', **largs):
        self.check_geometry_manager_name(method)
        gm = getattr(self, method)
        gm(**largs)
        
        for wobj, wargs in self.widgets:
            gm = getattr(wobj, self.layout_inside)
            gm(**wargs)

    def get_associated_data(self, name):
        v = self.associated_data.get(name, None)
        return v.get() if isinstance(v, tk.Variable) else v

    def init_variables(self):
       """継承先でUIと関連付ける変数を定義する"""
       pass
    def init_widgets(self):
        """継承先でUIの配置を定義する"""
        pass

#---
def main():
    root = tk.Tk()
    root.title("test")

    root.mainloop()


#----
if __name__ == "__main__":
    main()

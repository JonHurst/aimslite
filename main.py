import sys
import requests
from typing import List
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

import aimslib.common.types as T
import aimslib.detailed_roster.process as dr

from aimslib.output.csv import csv
from aimslib.output.ical import ical


class ModeSelector(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.role = None
        self.__make_widgets()


    def __make_widgets(self):
        RBW = 7

        frm_role = tk.Frame(self, relief=tk.SUNKEN, bd=2)
        frm_role.pack(fill=tk.X, expand=True, ipadx=5, pady=5)
        self.role = tk.StringVar()
        captain = ttk.Radiobutton(
            frm_role, text="Captain", variable=self.role,
            value='captain', width=RBW)
        captain.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        fo = ttk.Radiobutton(
            frm_role, text="FO", variable=self.role,
            value='fo', width=RBW)
        fo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        captain.invoke()


class Actions(tk.Frame):

    def __init__(self, parent, ms, txt):
        tk.Frame.__init__(self, parent)
        self.__make_widgets()
        self.ms = ms
        self.txt = txt
        self.last = None


    def __make_widgets(self):
        frm_1 = tk.Frame(self)
        frm_1.pack(fill=tk.X)
        btn_csv = ttk.Button(
            frm_1, text="Logbook (csv)",
            width=0, command=self.csv)
        btn_csv.pack(fill=tk.X)
        btn_ical = ttk.Button(
            frm_1, text="Roster (ical)",
            width=0, command=self.ical)
        btn_ical.pack(fill=tk.X)

        frm_2 = tk.Frame(self)
        frm_2.pack(fill=tk.X, pady=10)
        btn_save = ttk.Button(
            frm_2, text="Save",
            width=0, command=self.save)
        btn_save.pack(fill=tk.X)
        btn_copy = ttk.Button(
            frm_2, text="Copy",
            width=0, command=self.copy)
        btn_copy.pack(fill=tk.X)

        frm_3 = tk.Frame(self)
        frm_3.pack(fill=tk.X)
        btn_quit = ttk.Button(frm_3, text="Quit", width=0, command=sys.exit)
        btn_quit.pack(fill=tk.X)


    @staticmethod
    def __update_from_flightinfo(dutylist: List[T.Duty]) -> List[T.Duty]:
        retval: List[T.Duty] = []
        ids = []
        for duty in dutylist:
            ids.extend([f'{X.sched_start:%Y%m%dT%H%M}F{X.name}'
                        for X in duty.sectors
                        if X.flags == T.SectorFlags.NONE])
        try:
            r = requests.post(
                f"https://efwj6ola8d.execute-api.eu-west-1.amazonaws.com/default/reg",
                json={'flights': ids})
            r.raise_for_status()
            regntype_map = r.json()
        except requests.exceptions.RequestException:
            return dutylist #if anything goes wrong, just return input
        for duty in dutylist:
            updated_sectors: List[T.Sector] = []
            for sec in duty.sectors:
                flightid = f'{sec.sched_start:%Y%m%dT%H%M}F{sec.name}'
                if flightid in regntype_map:
                    reg, type_ = regntype_map[flightid]
                    updated_sectors.append(sec._replace(reg=reg, type_=type_))
                else:
                    updated_sectors.append(sec)
            retval.append(duty._replace(sectors=updated_sectors))
        return retval


    def csv(self):
        txt = ""
        dutylist, crewlist_map = [], {}
        f = filedialog.askopenfile(filetypes=(
            ("HTML", "*.htm"), ("HTML", "*.html"), ("All", "*.*")))
        if f:
            s = f.read()
            dutylist = self.__update_from_flightinfo(dr.duties(s))
            crewlist_map = dr.crew(s, dutylist)
        if not dutylist: return
        fo = True if self.ms.role.get() == 'fo' else False
        txt = csv(dutylist, crewlist_map, fo)
        self.txt.delete('1.0', tk.END)
        self.txt.insert(tk.END, txt)
        self.last = '.csv'


    def ical(self):
        dutylist = []
        f = filedialog.askopenfile(filetypes=(
            ("HTML", "*.htm"), ("HTML", "*.html"), ("All", "*.*")))
        if f:
            s = f.read()
            dutylist = dr.duties(s)
        if not dutylist: return
        txt = ical(dutylist)
        self.txt.delete('1.0', tk.END)
        self.txt.insert(tk.END, txt)
        self.last = '.ical'


    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.txt.get('1.0', tk.END))
        messagebox.showinfo('Copy', 'Text copied to clipboard.')


    def save(self):
        fn = filedialog.asksaveasfilename(
            defaultextension = self.last)
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.txt.get('1.0', tk.END))


class MainWindow(tk.Frame):

    def __init__(self, parent=None):
        tk.Frame.__init__(self, parent)
        self.__make_widgets()


    def __make_widgets(self):
        sidebar = tk.Frame(self, bd=2, width=0)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        txt = tk.Text(self)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(self)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb.config(command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        ms = ModeSelector(sidebar)
        ms.pack()
        ttk.Separator(sidebar, orient="horizontal").pack(fill=tk.X, pady=20)
        act = Actions(sidebar, ms, txt)
        act.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)


def main():
    root = tk.Tk()
    root.title("aimstool")
    MainWindow(root).pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

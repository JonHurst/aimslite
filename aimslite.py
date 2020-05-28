import requests
import os.path
import json
from typing import List
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

import aimslib.common.types as T
import aimslib.detailed_roster.process as dr

from aimslib.output.csv import csv
from aimslib.output.ical import ical


SETTINGS_FILE = os.path.expanduser("~/.aimstool")


class ModeSelector(ttk.Frame):

    def __init__(self, parent, txt, settings):
        ttk.Frame.__init__(self, parent)
        self.settings = settings
        self.txt = txt
        self.role = None
        self.output_type = None
        self.frm_csv_settings = None
        self.__make_widgets()


    def __make_widgets(self):
        frm_output_type = ttk.LabelFrame(self, text="Output type")
        frm_output_type.pack(fill=tk.X, expand=True, ipadx=5, pady=5)
        self.output_type = tk.StringVar()
        csv_output = ttk.Radiobutton(
            frm_output_type, text=" Logbook (csv)",
            variable=self.output_type, value='csv',
            command=self.output_type_changed)
        csv_output.pack(fill=tk.X)
        ical_output = ttk.Radiobutton(
            frm_output_type, text=" Roster (iCal)",
            variable=self.output_type, value='ical',
            command=self.output_type_changed)
        ical_output.pack(fill=tk.X)

        self.frm_csv_settings = ttk.LabelFrame(self, text="Role")
        self.role = tk.StringVar()
        captain = ttk.Radiobutton(
            self.frm_csv_settings, text="Captain",
            variable=self.role, value='captain',
            command=self.role_changed)
        captain.pack(fill=tk.X)
        fo = ttk.Radiobutton(
            self.frm_csv_settings, text="FO",
            variable=self.role, value='fo',
            command=self.role_changed)
        fo.pack(fill=tk.X)

        csv_output.invoke()


    def output_type_changed(self):
        assert self.output_type.get() in ('csv', 'ical')
        if self.output_type.get() == 'csv':
            self.frm_csv_settings.pack(fill=tk.X, expand=True, ipadx=5, pady=5)
            self.role.set(self.settings.get('Role', 'captain'))
        else:
            self.frm_csv_settings.pack_forget()
        self.txt.delete('1.0', tk.END)


    def role_changed(self):
        self.settings['Role'] = self.role.get()
        self.txt.delete('1.0', tk.END)


class Actions(ttk.Frame):

    def __init__(self, parent, ms, txt, settings):
        ttk.Frame.__init__(self, parent)
        self.__make_widgets()
        self.ms = ms
        self.txt = txt
        self.settings = settings


    def __make_widgets(self):
        frm_1 = ttk.Frame(self)
        frm_1.pack(fill=tk.X)
        btn_convert = ttk.Button(
            frm_1, text="Import",
            width=0, command=self.import_)
        btn_convert.pack(fill=tk.X)

        frm_2 = ttk.Frame(self)
        frm_2.pack(fill=tk.X, pady=10)
        btn_save = ttk.Button(
            frm_2, text="Save",
            width=0, command=self.save)
        btn_save.pack(fill=tk.X, pady=2)
        btn_copy = ttk.Button(
            frm_2, text="Copy",
            width=0, command=self.copy)
        btn_copy.pack(fill=tk.X, pady=2)

        frm_3 = ttk.Frame(self)
        frm_3.pack(fill=tk.X)
        btn_quit = ttk.Button(
            frm_3, text="Quit", width=0,
            command=self.winfo_toplevel().destroy)
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


    def __roster_html(self):
        retval = ""
        path = self.settings.get('openPath')
        fn = filedialog.askopenfilename(
            filetypes=(
                ("HTML file", "*.htm"),
                ("HTML file", "*.html"),
                ("All", "*.*")),
            initialdir=path)
        if fn:
            self.settings['openPath'] = os.path.dirname(fn)
            with open(fn) as f:
                retval = f.read()
        return retval


    def import_(self):
        assert self.ms.output_type.get() in ('csv', 'ical')
        try:
            if self.ms.output_type.get() == 'csv':
                self.csv()
            else:
                self.ical()
        except dr.DetailedRosterException as e:
            messagebox.showerror("Error", str(e))


    def csv(self):
        txt = ""
        dutylist, crewlist_map = [], {}
        html = self.__roster_html()
        if not html: return
        dutylist = self.__update_from_flightinfo(dr.duties(html))
        if not dutylist: return
        crewlist_map = dr.crew(html, dutylist)
        fo = True if self.ms.role.get() == 'fo' else False
        txt = csv(dutylist, crewlist_map, fo)
        self.txt.delete('1.0', tk.END)
        self.txt.insert(tk.END, txt)


    def ical(self):
        dutylist = []
        html = self.__roster_html()
        if not html: return
        dutylist = dr.duties(html)
        if not dutylist: return
        #note: normalise newlines for Text widget - will restore on output
        txt = ical(dutylist).replace("\r\n", "\n")
        self.txt.delete('1.0', tk.END)
        self.txt.insert(tk.END, txt)


    def copy(self):
        self.clipboard_clear()
        text = self.txt.get('1.0', tk.END)
        if self.ms.output_type == 'ical': #ical requires DOS style line endings
            text = text.replace("\n", "\r\n")
        self.clipboard_append(text)
        messagebox.showinfo('Copy', 'Text copied to clipboard.')


    def save(self):
        output_type = self.ms.output_type.get()
        assert  output_type in ('csv', 'ical')
        if output_type == 'csv':
            pathtype = 'csvSavePath'
            filetypes = (("CSV file", "*.csv"),
                         ("All", "*.*"))
            default_ext = '.csv'
        else:
            pathtype = 'icalSavePath'
            filetypes = (("ICAL file", "*.ics"),
                         ("ICAL file", "*.ical"),
                         ("All", "*.*"))
            default_ext = '.ics'
        path = self.settings.get(pathtype)
        fn = filedialog.asksaveasfilename(
            initialdir=path,
            filetypes=filetypes,
            defaultextension=default_ext)
        if fn:
            self.settings[pathtype] = os.path.dirname(fn)
            with open(fn, "w", encoding="utf-8", newline='') as f:
                text = self.txt.get('1.0', tk.END)
                if output_type == 'ical': #ical requires DOS style line endings
                    text = text.replace("\n", "\r\n")
                f.write(text)
                messagebox.showinfo('Saved', f'Save complete.')


class TextWithSyntaxHighlighting(tk.Text):

    def __init__(self, parent=None, **kwargs):
        tk.Text.__init__(self, parent, background='white', **kwargs)
        self.tag_configure("grayed", foreground="#B0B0B0")
        self.tag_configure("keyword", foreground="green")
        self.tag_configure("datetime", foreground="blue")
        self.bind('<KeyRelease>', lambda *args: self.highlight_syntax())

    def insert(self, idx, text, *args):
        tk.Text.insert(self, idx, text, *args)
        self.highlight_syntax()


    def highlight_syntax(self):
        for tag in ("keyword", "datetime", "grayed"):
            self.tag_remove(tag, "1.0", "end")
        text = self.get("1.0", "1.end")
        if text.startswith("BEGIN:VCALENDAR"):
            self.highlight_vcalendar()
        else:
            self.highlight_csv()


    def highlight_vcalendar(self):
        count = tk.IntVar()
        start_idx = "1.0"
        while True:
            new_idx = self.search(
                "BEGIN:VEVENT", start_idx, count=count,
                stopindex = "end")
            if not new_idx: break
            start_idx = f"{new_idx} + {count.get()} chars"
            self.tag_add("keyword", new_idx, start_idx)
        start_idx = "1.0"
        while True:
            new_idx = self.search(
                r"^[\w-]+:",
                start_idx, count=count, regexp=True,
                stopindex = "end")
            if not new_idx: break
            start_idx = f"{new_idx} + {count.get()} chars"
            self.tag_add("grayed", new_idx, start_idx)
        start_idx = "1.0"
        while True:
            new_idx = self.search(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}",
                start_idx, count=count, regexp=True,
                stopindex = "end")
            if not new_idx: break
            start_idx = f"{new_idx} + {count.get()} chars"
            self.tag_add("datetime", new_idx, start_idx)


    def highlight_csv(self):
        count = tk.IntVar()
        start_idx = "1.0"
        while True:
            new_idx = self.search(
                r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
                start_idx, count=count, regexp=True,
                stopindex = "end")
            if not new_idx: break
            start_idx = f"{new_idx} + {count.get()} chars"
            self.tag_add("datetime", new_idx, start_idx)
        start_idx = "1.0"
        while True:
            new_idx = self.search(
                r'(:00)?[",]+',
                start_idx, count=count, regexp=True,
                stopindex = "end")
            if not new_idx: break
            start_idx = f"{new_idx} + {count.get()} chars"
            self.tag_add("grayed", new_idx, start_idx)


class MainWindow(ttk.Frame):

    def __init__(self, parent=None):
        ttk.Frame.__init__(self, parent)
        try:
            with open(SETTINGS_FILE) as f:
                self.settings = json.load(f)
        except:
            self.settings = {}
        self.__make_widgets()


    def __make_widgets(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sb = ttk.Scrollbar(self)
        sb.grid(row=0, column=2, sticky=tk.NS)
        sidebar = ttk.Frame(self, width=0)
        sidebar.grid(row=0, column=0, sticky=tk.NS, padx=5, pady=5)
        txt = TextWithSyntaxHighlighting(self)
        txt.grid(row=0, column=1, sticky=tk.NSEW)
        sb.config(command=txt.yview)
        txt.config(yscrollcommand=sb.set)

        sidebar.rowconfigure(1, weight=1)
        ms = ModeSelector(sidebar, txt, self.settings)
        ms.grid(row=0, sticky=tk.N)
        act = Actions(sidebar, ms, txt, self.settings)
        act.grid(row=1, sticky=(tk.EW + tk.S))


    def destroy(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)
        ttk.Frame.destroy(self)


def main():
    root = tk.Tk()
    root.title("aimstool")
    mw = MainWindow(root)
    mw.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

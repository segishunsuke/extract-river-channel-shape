# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import csv
import os

from river_extractor import RiverCrossSectionExtractor  # クラス化済みコードをインポート

class RiverExtractorGUI:
    def __init__(self, master):
        self.master = master
        self.extractor = RiverCrossSectionExtractor()
        self.master.title("河道横断面抽出ツール")

        self.notebook = ttk.Notebook(master)
        self.setting_frame = tk.Frame(self.notebook)
        self.basic_frame = tk.Frame(self.notebook)
        self.notebook.add(self.setting_frame, text="横断面別設定・実行")
        self.notebook.add(self.basic_frame, text="基本パラメータ")
        self.notebook.pack(fill="both", expand=True)

        # setting.csv タブ
        self.tree_setting, self.scrolls_setting = self.create_treeview(self.setting_frame)
        self.load_setting_csv()

        self.save_button_setting = tk.Button(self.setting_frame, text="横断面別設定を保存", command=self.save_setting)
        self.save_button_setting.pack(pady=2)
        
        self.set_flows_button = tk.Button(self.setting_frame, text="J-FlwDirを利用し流量設定", command=self.set_flows_using_jflwdir)
        self.set_flows_button.pack(pady=2)
        
        self.run_button = tk.Button(self.setting_frame, text="河道横断面抽出実行", command=self.run_extraction)
        self.run_button.pack(pady=2)

        self.progress = ttk.Progressbar(self.setting_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=2)

        self.progress_label = tk.Label(self.setting_frame, text="", width=30, anchor=tk.CENTER)
        self.progress_label.pack()

        self.log = tk.Text(self.setting_frame, height=10)
        self.log.pack(fill="both", expand=True, padx=10, pady=5)

        # basic_parameters.csv タブ
        self.tree_basic, self.scrolls_basic = self.create_treeview(self.basic_frame, use_row_header=True)
        self.load_basic_parameters_csv()

        self.save_button_basic = tk.Button(self.basic_frame, text="保存", command=self.save_basic_parameters)
        self.save_button_basic.pack(pady=5)

    def create_treeview(self, parent_frame, use_row_header=False):
        frame = tk.Frame(parent_frame, width=700, height=250)
        frame.pack_propagate(False)
        frame.pack(fill="x", pady=5)

        x_scroll = tk.Scrollbar(frame, orient="horizontal")
        x_scroll.pack(side="bottom", fill="x")

        y_scroll = tk.Scrollbar(frame, orient="vertical")
        y_scroll.pack(side="right", fill="y")

        tree = ttk.Treeview(
            frame, show="headings" if not use_row_header else "tree",
            xscrollcommand=x_scroll.set,
            yscrollcommand=y_scroll.set
        )
        tree.pack(side="left", fill="both", expand=True)

        x_scroll.config(command=tree.xview)
        y_scroll.config(command=tree.yview)

        tree.bind("<Double-1>", lambda event, t=tree: self.edit_cell(event, t))
        return tree, (x_scroll, y_scroll)

    def load_setting_csv(self):
        filename = "setting.csv"
        if not os.path.exists(filename):
            self.extractor.export_setting()

        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)

        self.tree_setting.delete(*self.tree_setting.get_children())

        self.tree_setting["columns"] = [str(i) for i in range(len(data[0]))]
        for i, header in enumerate(data[0]):
            col = str(i)
            self.tree_setting.heading(col, text=header)
            self.tree_setting.column(col, width=80, anchor="center", stretch=False)

        self.insert_rows_chunked(self.tree_setting, data[1:], start=0, chunk_size=100)

    def load_basic_parameters_csv(self):
        filename = "basic_parameters.csv"
        if not os.path.exists(filename):
            return

        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)

        self.tree_basic.delete(*self.tree_basic.get_children())
        self.tree_basic["columns"] = ["value"]
        self.tree_basic.heading("value", text="設定値")
        self.tree_basic.column("value", width=100, anchor="center", stretch=False)

        for row in data:
            if len(row) < 2:
                continue
            param_name = row[0]
            value = row[1]
            self.tree_basic.insert("", "end", iid=param_name, text=param_name, values=[value])
    
    def insert_rows_chunked(self, tree, rows, start=0, chunk_size=100):
        end = min(start + chunk_size, len(rows))
        for i in range(start, end):
            tree.insert("", "end", values=rows[i])
        if end < len(rows):
            self.master.after(10, lambda: self.insert_rows_chunked(tree, rows, end, chunk_size))
    
    def save_setting(self):
        with open("setting.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([self.tree_setting.heading(col)["text"] for col in self.tree_setting["columns"]])
            for row_id in self.tree_setting.get_children():
                writer.writerow(self.tree_setting.item(row_id)["values"])
        try:
            self.extractor.read_setting()
            messagebox.showinfo("保存完了", "setting.csvを保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"パラメータの反映中にエラーが発生しました:\n{e}")

    def save_basic_parameters(self):
        with open("basic_parameters.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row_id in self.tree_basic.get_children():
                param_name = row_id
                value = self.tree_basic.item(row_id)["values"][0]
                writer.writerow([param_name, value])
        try:
            self.extractor.read_basic_parameters()
            messagebox.showinfo("保存完了", "basic_parameters.csvを保存し，パラメータを反映しました。")
        except Exception as e:
            messagebox.showerror("エラー", f"パラメータの反映中にエラーが発生しました:\n{e}")

    def edit_cell(self, event, tree):
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = tree.identify_row(event.y)
        col = tree.identify_column(event.x)

        x, y, width, height = tree.bbox(row_id, col)
        value = tree.set(row_id, col)

        entry = tk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus()

        def save_edit(event):
            tree.set(row_id, col, entry.get())
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def set_flows_using_jflwdir(self):
        self.log.insert(tk.END, "横断面別流量設定開始...\n")
        self.log.see(tk.END)
        
        def run_in_thread():
            try:
                self.extractor.use_jflwdir_to_set_flow(progress_callback=self.update_progress)
                self.log.insert(tk.END, "横断面別流量設定完了\n")
                self.load_setting_csv()  # 実行後に自動再読み込み
            except Exception as e:
                self.log.insert(tk.END, f"エラー: {e}\n")
            self.log.see(tk.END)
        
        threading.Thread(target=run_in_thread, daemon=True).start()

    def run_extraction(self):
        self.log.insert(tk.END, "河道横断面抽出開始...\n")
        self.log.see(tk.END)
        
        def run_in_thread():
            try:
                self.extractor.run(progress_callback=self.update_progress)
                self.log.insert(tk.END, "河道横断面抽出完了\n")
                self.load_setting_csv()  # 実行後に自動再読み込み
            except Exception as e:
                self.log.insert(tk.END, f"エラー: {e}\n")
            self.log.see(tk.END)
        
        threading.Thread(target=run_in_thread, daemon=True).start()

    def update_progress(self, current, total, message):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.progress_label.config(text=message)
        self.master.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = RiverExtractorGUI(root)
    root.mainloop()

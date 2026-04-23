# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import csv
import os
from river_extractor import RiverCrossSectionExtractor  # クラス化済みコードをインポート

class RiverExtractorGUI:
    def __init__(self, master):
        self.master = master
        self.extractor = RiverCrossSectionExtractor()
        self.master.title("河道横断面抽出ツール")
        
        self.master.geometry("600x600")

        self.notebook = ttk.Notebook(master)
        self.setting_frame = tk.Frame(self.notebook)
        self.basic_frame = tk.Frame(self.notebook)
        self.notebook.add(self.setting_frame, text="横断面別設定・実行")
        self.notebook.add(self.basic_frame, text="基本パラメータ")
        self.notebook.pack(fill="both", expand=True)

        self.desc_label = tk.Label(self.setting_frame, text="※ 自動推測を行う場合、tol2 = 0 なら「堤防無し」として処理します。", fg="gray")
        self.desc_label.pack(anchor="w", padx=10, pady=(5, 0))

        self.tree_setting, self.scrolls_setting = self.create_treeview(self.setting_frame)
        self.load_setting_csv()

        self.mode_frame = tk.LabelFrame(self.setting_frame, text="設定プリセット一括切替（選択行に適用）")
        self.mode_frame.pack(fill="x", padx=10, pady=5)

        self.target_frame = tk.Frame(self.mode_frame)
        self.target_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(self.target_frame, text="適用対象:").pack(side="left")
        self.target_side_var = tk.StringVar(value="both")
        ttk.Radiobutton(self.target_frame, text="両岸", variable=self.target_side_var, value="both").pack(side="left", padx=5)
        ttk.Radiobutton(self.target_frame, text="左岸のみ", variable=self.target_side_var, value="left").pack(side="left", padx=5)
        ttk.Radiobutton(self.target_frame, text="右岸のみ", variable=self.target_side_var, value="right").pack(side="left", padx=5)

        # 同じ行の右端に「前回結果をリセット」ボタンを配置
        self.btn_reset_inter = tk.Button(self.target_frame, text="前回結果を不使用", command=self.reset_intermediate)
        self.btn_reset_inter.pack(side="right", padx=5)

        # プリセットボタン＆角度調整ボタン群（1行にまとめる）
        self.btn_frame = tk.Frame(self.mode_frame)
        self.btn_frame.pack(fill="x", padx=5, pady=2)

        self.btn_default = tk.Button(self.btn_frame, text="自動推測・堤防有り", command=lambda: self.apply_preset("default"))
        self.btn_default.pack(side="left", padx=2)

        self.btn_no_levee = tk.Button(self.btn_frame, text="自動推測・堤防無し", command=lambda: self.apply_preset("no_levee"))
        self.btn_no_levee.pack(side="left", padx=2)

        self.btn_limit = tk.Button(self.btn_frame, text="限界線手動設定", command=lambda: self.apply_preset("limit"))
        self.btn_limit.pack(side="left", padx=2)

        tk.Label(self.btn_frame, text=" | 回転角:").pack(side="left", padx=(10, 0))
        self.btn_angle_p10 = tk.Button(self.btn_frame, text="+10度", command=lambda: self.adjust_angle(10))
        self.btn_angle_p10.pack(side="left", padx=2)
        self.btn_angle_m10 = tk.Button(self.btn_frame, text="-10度", command=lambda: self.adjust_angle(-10))
        self.btn_angle_m10.pack(side="left", padx=2)

        self.action_frame = tk.Frame(self.setting_frame)
        self.action_frame.pack(fill="x", padx=10, pady=2)

        self.save_button_setting = tk.Button(self.action_frame, text="横断面別設定を保存", command=self.save_setting)
        self.save_button_setting.pack(side="left", padx=5)
        
        self.set_flows_button = tk.Button(self.action_frame, text="J-FlwDirを利用し流量設定", command=self.set_flows_using_jflwdir)
        self.set_flows_button.pack(side="left", padx=5)
        
        self.run_button = tk.Button(self.action_frame, text="河道横断面抽出実行", command=self.run_extraction)
        self.run_button.pack(side="right", padx=5)

        self.progress = ttk.Progressbar(self.setting_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=2)

        self.progress_label = tk.Label(self.setting_frame, text="", width=30, anchor=tk.CENTER)
        self.progress_label.pack()

        self.log = tk.Text(self.setting_frame, height=10)
        self.log.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree_basic, self.scrolls_basic = self.create_treeview(self.basic_frame, use_row_header=True)
        self.load_basic_parameters_csv()

        self.save_button_basic = tk.Button(self.basic_frame, text="保存", command=self.save_basic_parameters)
        self.save_button_basic.pack(pady=5)

    def create_treeview(self, parent_frame, use_row_header=False):
        frame = tk.Frame(parent_frame, width=600, height=250)
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
        filename = "settings.csv"
        if not os.path.exists(filename):
            self.extractor.export_setting()

        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)

        self.csv_headers = data[0]

        self.tree_setting.delete(*self.tree_setting.get_children())
        self.tree_setting["columns"] = [str(i) for i in range(len(data[0]))]
        
        column_settings = {
            "Distance": ("距離", 60),
            "Use intermediate result": ("前回結果使用", 90),
            "Flow": ("流量", 50),
            "Angle adjustment": ("回転角", 50),
            "Left Mode": ("左手動", 50),
            "Left tol2": ("左tol2", 50),
            "Right Mode": ("右手動", 50),
            "Right tol2": ("右tol2", 50)
        }

        for i, header in enumerate(data[0]):
            col = str(i)
            if header in column_settings:
                display_text = column_settings[header][0]
                col_width = column_settings[header][1]
            else:
                display_text = header
                col_width = 80

            self.tree_setting.heading(col, text=display_text)
            self.tree_setting.column(col, width=col_width, anchor="center", stretch=False)

        try:
            headers = data[0]
            display_indices = [
                str(headers.index("Distance")),
                str(headers.index("Use intermediate result")),
                str(headers.index("Flow")),
                str(headers.index("Angle adjustment")),
                str(headers.index("Left Mode")),
                str(headers.index("Left tol2")),
                str(headers.index("Right Mode")),
                str(headers.index("Right tol2"))
            ]
            self.tree_setting["displaycolumns"] = display_indices
        except ValueError:
            pass

        self.insert_rows_chunked(self.tree_setting, data[1:], start=0, chunk_size=100)

    # 選択された行の「前回結果使用」を 0 にリセットする処理
    def reset_intermediate(self):
        selected_items = self.tree_setting.selection()
        if not selected_items:
            messagebox.showwarning("警告", "対象の行（断面）を選択してください。")
            return

        try:
            idx_inter = self.csv_headers.index("Use intermediate result")
        except ValueError:
            return

        for item in selected_items:
            values = list(self.tree_setting.item(item, "values"))
            values[idx_inter] = "0"
            self.tree_setting.item(item, values=values)

        self.save_setting(show_msg=False)
        self.log.insert(tk.END, f"{len(selected_items)}件の断面の「前回結果使用」を 0 にリセットしました。\n")
        self.log.see(tk.END)

    def adjust_angle(self, delta):
        selected_items = self.tree_setting.selection()
        if not selected_items:
            messagebox.showwarning("警告", "対象の行（断面）を選択してください。")
            return

        try:
            idx_angle = self.csv_headers.index("Angle adjustment")
            idx_inter = self.csv_headers.index("Use intermediate result")
        except ValueError:
            return

        for item in selected_items:
            values = list(self.tree_setting.item(item, "values"))
            values[idx_inter] = "0"  # 再計算フラグ
            
            # 数値を足して文字列に戻す
            current_val = float(values[idx_angle])
            values[idx_angle] = str(round(current_val + delta, 1))
            self.tree_setting.item(item, values=values)

        self.save_setting(show_msg=False)
        self.log.insert(tk.END, f"{len(selected_items)}件の断面の回転角を {delta:+}度 変更しました。\n")
        self.log.see(tk.END)

    def apply_preset(self, preset_type):
        selected_items = self.tree_setting.selection()
        if not selected_items:
            messagebox.showwarning("警告", "対象の行（断面）を選択してください。")
            return

        target_side = self.target_side_var.get()

        headers = self.csv_headers 
        try:
            idx_inter = headers.index("Use intermediate result")
            idx_l_mode = headers.index("Left Mode")
            idx_r_mode = headers.index("Right Mode")
            idx_l_tol1 = headers.index("Left tol1")
            idx_l_tol2 = headers.index("Left tol2")
            idx_l_tol3 = headers.index("Left tol3")
            idx_r_tol1 = headers.index("Right tol1")
            idx_r_tol2 = headers.index("Right tol2")
            idx_r_tol3 = headers.index("Right tol3")
        except ValueError:
            messagebox.showerror("エラー", "settings.csv に必要な列が見つかりません。")
            return

        for item in selected_items:
            values = list(self.tree_setting.item(item, "values"))
            values[idx_inter] = "0"

            if preset_type == "limit":
                if target_side in ["both", "left"]:
                    values[idx_l_mode] = "1"
                if target_side in ["both", "right"]:
                    values[idx_r_mode] = "1"
                
            elif preset_type == "no_levee":
                if target_side in ["both", "left"]:
                    values[idx_l_mode] = "0"
                    values[idx_l_tol1] = str(self.extractor.tol1)
                    values[idx_l_tol2] = "0.0"
                    values[idx_l_tol3] = str(self.extractor.tol3)
                if target_side in ["both", "right"]:
                    values[idx_r_mode] = "0"
                    values[idx_r_tol1] = str(self.extractor.tol1)
                    values[idx_r_tol2] = "0.0"
                    values[idx_r_tol3] = str(self.extractor.tol3)
                
            elif preset_type == "default":
                if target_side in ["both", "left"]:
                    values[idx_l_mode] = "0"
                    values[idx_l_tol1] = str(self.extractor.tol1)
                    values[idx_l_tol2] = str(self.extractor.tol2)
                    values[idx_l_tol3] = str(self.extractor.tol3)
                if target_side in ["both", "right"]:
                    values[idx_r_mode] = "0"
                    values[idx_r_tol1] = str(self.extractor.tol1)
                    values[idx_r_tol2] = str(self.extractor.tol2)
                    values[idx_r_tol3] = str(self.extractor.tol3)

            self.tree_setting.item(item, values=values)

        self.save_setting(show_msg=False)

        preset_names = {"default": "自動推測・堤防有り", "no_levee": "自動推測・堤防無し", "limit": "限界線手動設定"}
        target_names = {"both": "両岸", "left": "左岸のみ", "right": "右岸のみ"}
        msg = f"{len(selected_items)}件の断面の「{target_names[target_side]}」を「{preset_names[preset_type]}」に変更し、保存しました。\n"
        
        self.log.insert(tk.END, msg)
        self.log.see(tk.END)

    def load_basic_parameters_csv(self):
        filename = "./input/basic_parameters.csv"
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
    
    def save_setting(self, show_msg=True):
        try:
            with open("settings.csv", "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)
                for row_id in self.tree_setting.get_children():
                    writer.writerow(self.tree_setting.item(row_id)["values"])
            
            if show_msg:
                messagebox.showinfo("保存完了", "settings.csvを保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"settings.csvの保存中にエラーが発生しました:\n{e}")

    def save_basic_parameters(self):
        try:
            with open("./input/basic_parameters.csv", "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row_id in self.tree_basic.get_children():
                    param_name = row_id
                    value = self.tree_basic.item(row_id)["values"][0]
                    writer.writerow([param_name, value])
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
        flow_ratio = simpledialog.askfloat("比流量入力", "比流量[(m3/s) / km2]を入力してください:")
        if flow_ratio is None:
            return
        
        self.log.insert(tk.END, "横断面別流量設定開始...\n")
        self.log.see(tk.END)
        
        def run_in_thread():
            try:
                self.extractor.use_jflwdir_to_set_flow(flow_ratio, progress_callback=self.update_progress)
                self.log.insert(tk.END, "横断面別流量設定完了\n")
                self.load_setting_csv()
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
                self.load_setting_csv()
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

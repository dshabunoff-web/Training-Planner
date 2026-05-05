import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import json
import os

# ---------- Модели данных ---------- #

class Training:
    def __init__(self, ttype: str, volume: float, unit: str, date_str: str, notes: str = ""):
        # ttype: тип тренировки (Силовая, Кардио, Гибкость и т.д.)
        self.ttype = ttype
        self.volume = float(volume)  # например, минуты или число повторений
        self.unit = unit  # единицы измерения (мин, повторения, сет)
        self.date = date.fromisoformat(date_str)
        self.notes = notes

    def to_dict(self):
        return {
            "ttype": self.ttype,
            "volume": self.volume,
            "unit": self.unit,
            "date": self.date.isoformat(),
            "notes": self.notes
        }

    @staticmethod
    def from_dict(d):
        return Training(d["ttype"], d["volume"], d["unit"], d["date"], d.get("notes", ""))

# ---------- Приложение ---------- #

class TrainingPlannerApp:
    HISTORY_FILE = "training_history.json"
    FAVORITES_FILE = "training_favorites.json"

    def __init__(self, root):
        self.root = root
        self.root.title("Training Planner")
        self.root.geometry("1000x650")

        self.plan = []        # текущий план тренировок
        self.history = []     # история добавлений/проверки
        self.favorites = []   # избранные тренировки

        self._setup_ui()
        self._load_history()
        self._load_favorites()

    def _setup_ui(self):
        # Верхняя панель добавления новой тренировки
        add_frame = ttk.Frame(self.root, padding=10)
        add_frame.pack(fill="x")

        ttk.Label(add_frame, text="Тип тренировки:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.type_var = tk.StringVar(value="Силовая")
        self.type_cb = ttk.Combobox(add_frame, textvariable=self.type_var, state="readonly",
                                    values=["Силовая", "Кардио", "Гибкость", "Йога", "Пауэрлифтер", "Другое"])
        self.type_cb.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(add_frame, text="Объём:").grid(row=0, column=2, sticky="e", padx=4, pady=2)
        self.volume_var = tk.StringVar(value="30")
        ttk.Entry(add_frame, textvariable=self.volume_var, width=10).grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(add_frame, text="Единицы:").grid(row=0, column=4, sticky="e", padx=4, pady=2)
        self.unit_var = tk.StringVar(value="мин")
        self.unit_cb = ttk.Combobox(add_frame, textvariable=self.unit_var, state="readonly",
                                    values=["мин", "повторений", "сет"])
        self.unit_cb.grid(row=0, column=5, padx=4, pady=2)
        self.unit_cb.current(0)

        ttk.Label(add_frame, text="Дата (YYYY-MM-DD):").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(add_frame, textvariable=self.date_var, width=15).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(add_frame, text="Заметки:").grid(row=1, column=2, sticky="e", padx=4, pady=2)
        self.notes_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.notes_var, width=40).grid(row=1, column=3, columnspan=3, padx=4, pady=2)

        ttk.Button(add_frame, text="Добавить тренировку", command=self.add_training).grid(row=0, column=6, rowspan=2, padx=6, pady=2)

        # Раздел фильтров и статистики
        filter_stat_frame = ttk.Frame(self.root, padding=10)
        filter_stat_frame.pack(fill="x")

        ttk.Label(filter_stat_frame, text="Фильтры:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")

        ttk.Label(filter_stat_frame, text="Начальная дата:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.start_date_var = tk.StringVar()
        ttk.Entry(filter_stat_frame, textvariable=self.start_date_var, width=12).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(filter_stat_frame, text="Тип:").grid(row=1, column=2, sticky="e", padx=4, pady=2)
        self.filter_type_var = tk.StringVar(value="Все")
        self.filter_type_cb = ttk.Combobox(filter_stat_frame, textvariable=self.filter_type_var, state="readonly",
                                           values=["Все", "Силовая", "Кардио", "Гибкость", "Йога", "Пауэрлифтер", "Другое"])
        self.filter_type_cb.grid(row=1, column=3, padx=4, pady=2)
        self.filter_type_cb.current(0)

        ttk.Button(filter_stat_frame, text="Применить фильтр", command=self.apply_filters).grid(row=1, column=4, padx=6)
        ttk.Button(filter_stat_frame, text="Сбросить фильтры", command=self.reset_filters).grid(row=1, column=5, padx=6)

        # Основная таблица плана
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(main_frame, columns=("date","type","volume","unit","notes"), show="headings")
        self.tree.heading("date", text="Дата")
        self.tree.heading("type", text="Тип")
        self.tree.heading("volume", text="Объём")
        self.tree.heading("unit", text="Единицы")
        self.tree.heading("notes", text="Заметки")
        self.tree.column("date", width=110)
        self.tree.column("type", width=120)
        self.tree.column("volume", width=80, anchor="e")
        self.tree.column("unit", width=80)
        self.tree.column("notes", width=380)
        self.tree.pack(fill="both", expand=True)

        # Контроль редактирования и удаления
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill="x", pady=6)
        ttk.Button(ctrl_frame, text="Удалить выбранное", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(ctrl_frame, text="Экспорт плана", command=self.export_plan).pack(side="left", padx=6)
        ttk.Button(ctrl_frame, text="Импорт плана", command=self.import_plan).pack(side="left")

        # Подсчёт общего объёма за период
        summary_frame = ttk.Frame(self.root, padding=10)
        summary_frame.pack(fill="x")
        self.summary_var = tk.StringVar(value="Итого за период: 0.0 ед.")
        ttk.Label(summary_frame, textvariable=self.summary_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")

        # Меню
        self._setup_menu()

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Сохранить как...", command=self.export_plan)
        filemenu.add_command(label="Импорт плана", command=self.import_plan)
        filemenu.add_separator()
        filemenu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=helpmenu)

    def _show_about(self):
        messagebox.showinfo("О программе", "Training Planner — планирование тренировок с фильтрацией, экспортом/импортом JSON и Git.")

    # ---------- Работа с планом ---------- #

    def add_training(self):
        ttype = self.type_var.get()
        try:
            volume = float(self.volume_var.get())
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Объём должен быть числом.")
            return
        unit = self.unit_var.get()
        date_str = self.date_var.get()
        try:
            date.fromisoformat(date_str)
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Дата должна быть в формате YYYY-MM-DD.")
            return
        notes = self.notes_var.get()

        tr = Training(ttype, volume, unit, date_str, notes)
        self.plan.append(tr)
        self._append_to_plan_tree(tr)
        self.clear_add_form()
        self._save_plan()
        self._update_summary()

    def _append_to_plan_tree(self, tr: Training):
        self.tree.insert("", "end", values=(tr.date.isoformat(), tr.ttype, f"{tr.volume:.2f}", tr.unit, tr.notes))

    def clear_add_form(self):
        self.volume_var.set("30")
        self.date_var.set(date.today().isoformat())
        self.notes_var.set("")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Нет выбора", "Выберите элемент в списке.")
            return
        idx = self.tree.index(sel[0])
        del self.plan[idx]
        self.tree.delete(sel[0])
        self._save_plan()
        self._update_summary()

    def export_plan(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        data = [tr.to_dict() for tr in self.plan]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Успех", "План экспортирован.")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_plan(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.plan = [Training.from_dict(d) for d in data]
            self._refresh_plan_tree()
            self._save_plan()
            self._update_summary()
            messagebox.showinfo("Успех", "План импортирован.")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    def _refresh_plan_tree(self):
        self.tree.delete(*self.tree.get_children())
        for tr in self.plan:
            self._append_to_plan_tree(tr)

    def _save_plan(self):
        # простая локальная запись плана в файл
        data = [t.to_dict() for t in self.plan]
        with open("training_plan.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ---------- История и фильтры ---------- #

    def _load_history(self):
        if not os.path.exists(self.HISTORY_FILE):
            self.history = []
            return
        try:
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        except Exception as e:
            messagebox.showwarning("Чтение истории", f"Не удалось загрузить историю: {e}")

    def _save_history(self):
        try:
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showwarning("Сохранение истории", f"Не удалось сохранить историю: {e}")

    def apply_filters(self):
        start = self.start_date_var.get()
        ftype = self.filter_type_var.get()
        self._filter_and_update(start, ftype)

    def _filter_and_update(self, start, ftype):
        self.tree.delete(*self.tree.get_children())
        total = 0.0
        for tr in self.plan:
            if start:
                try:
                    dt = tr.date
                    start_dt = date.fromisoformat(start)
                    if dt < start_dt:
                        continue
                except ValueError:
                    pass
            if ftype != "Все" and tr.ttype != ftype:
                continue
            self._append_to_plan_tree(tr)
            total += tr.volume
        self._update_summary(total)

    def reset_filters(self):
        self.start_date_var.set("")
        self.filter_type_var.set("Все")
        self.apply_filters()

    def _update_summary(self, total=None):
        if total is None:
            total = sum(t.volume for t in self.plan)
        self.summary_var.set(f"Итого за период: {total:.2f} ед. {self._unit_label()}")

    def _unit_label(self):
        # простая метка единиц в зависимости от планов, например если есть минуты
        return ""

    # ---------- JSON и Git ---------- #
    def _load_favorites(self):
        if not os.path.exists(self.FAVORITES_FILE):
            self.favorites = []
            return
        try:
            with open(self.FAVORITES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.favorites = data
            self._refresh_favorites()
        except Exception as e:
            messagebox.showwarning("Чтение избранного", f"Не удалось загрузить избранное: {e}")

    def _refresh_favorites(self):
        # простой refresh списка избранного
        pass  # можно реализовать отображение избранного в отдельной панели

# ---------- Запуск ---------- #

def main():
    root = tk.Tk()
    app = TrainingPlannerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
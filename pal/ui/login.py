"""
Diálogo de Login para PAL (Tkinter)
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

class LoginDialog:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.top = tk.Toplevel(root)
        self.top.title("Iniciar Sesión")
        self.top.geometry("360x200")
        self.top.transient(root)
        self.top.grab_set()
        self.result = None

        frm = ttk.Frame(self.top, padding=20)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Usuario:").grid(row=0, column=0, sticky="w")
        self.username = ttk.Entry(frm)
        self.username.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frm, text="Contraseña:").grid(row=1, column=0, sticky="w")
        self.password = ttk.Entry(frm, show="*")
        self.password.grid(row=1, column=1, sticky="ew", pady=5)

        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, pady=15, sticky="e")
        ttk.Button(btns, text="Cancelar", command=self.top.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btns, text="Entrar", command=self._ok).pack(side=tk.RIGHT)

        self.username.focus_set()
        self.top.bind('<Return>', lambda e: self._ok())
        self.top.bind('<Escape>', lambda e: self.top.destroy())

    def _ok(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()
        if not user or not pwd:
            return
        self.result = (user, pwd)
        self.top.destroy()

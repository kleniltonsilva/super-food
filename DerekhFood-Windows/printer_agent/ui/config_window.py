# printer_agent/ui/config_window.py

"""
Janela de configuração usando tkinter.
Login do restaurante + seleção de impressoras por setor.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
from typing import Optional, Callable

from ..config import load_config, save_config, get_app_dir
from ..api_client import ApiClient
from ..print_driver import listar_impressoras

logger = logging.getLogger("printer_agent.config_ui")


class ConfigWindow:
    """Janela de configuração do Printer Agent."""

    def __init__(self, on_save: Optional[Callable] = None):
        self.on_save = on_save
        self.config = load_config()
        self._root = None

    def mostrar(self):
        """Abre a janela de configuração."""
        self._root = tk.Tk()
        self._root.title("Derekh Food - Configuração da Impressora")
        self._root.geometry("500x620")
        self._root.resizable(False, False)

        # Estilo
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"))

        # Container principal com padding
        main = ttk.Frame(self._root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(main, text="Derekh Food - Impressora", style="Title.TLabel").pack(pady=(0, 15))

        # ─── Seção: Servidor ───
        ttk.Label(main, text="Servidor", style="Section.TLabel").pack(anchor=tk.W)
        self._server_var = tk.StringVar(value=self.config.get("server_url", "wss://superfood-api.fly.dev"))
        ttk.Entry(main, textvariable=self._server_var, width=60).pack(fill=tk.X, pady=(2, 10))

        # ─── Seção: Login ───
        ttk.Label(main, text="Login do Restaurante", style="Section.TLabel").pack(anchor=tk.W)

        login_frame = ttk.Frame(main)
        login_frame.pack(fill=tk.X, pady=(2, 5))

        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._email_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self._email_var, width=35).grid(row=0, column=1, padx=(5, 0), pady=2)

        ttk.Label(login_frame, text="Senha:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._senha_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self._senha_var, show="*", width=35).grid(row=1, column=1, padx=(5, 0), pady=2)

        self._login_btn = ttk.Button(main, text="Conectar", command=self._fazer_login)
        self._login_btn.pack(pady=(0, 10))

        # Status do login
        self._login_status = tk.StringVar(value="Não conectado" if not self.config.get("token") else f"Conectado (ID: {self.config.get('restaurante_id', '?')})")
        ttk.Label(main, textvariable=self._login_status, foreground="gray").pack(pady=(0, 10))

        # ─── Seção: Impressoras ───
        ttk.Label(main, text="Impressoras por Setor", style="Section.TLabel").pack(anchor=tk.W, pady=(5, 0))

        printers = listar_impressoras()
        printer_options = ["(Nenhuma)"] + printers

        imp_frame = ttk.Frame(main)
        imp_frame.pack(fill=tk.X, pady=(2, 10))

        self._printer_vars = {}
        setores = [
            ("geral", "Geral (todas as comandas)"),
            ("cozinha", "Cozinha"),
            ("bar", "Bar / Bebidas"),
            ("caixa", "Caixa"),
        ]

        for i, (setor, label) in enumerate(setores):
            ttk.Label(imp_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value=self.config.get("impressoras", {}).get(setor) or "(Nenhuma)")
            self._printer_vars[setor] = var
            combo = ttk.Combobox(imp_frame, textvariable=var, values=printer_options, width=35, state="readonly")
            combo.grid(row=i, column=1, padx=(5, 0), pady=2)

        # ─── Seção: Opções ───
        ttk.Label(main, text="Opções", style="Section.TLabel").pack(anchor=tk.W, pady=(5, 0))

        opts_frame = ttk.Frame(main)
        opts_frame.pack(fill=tk.X, pady=(2, 10))

        ttk.Label(opts_frame, text="Largura:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._largura_var = tk.StringVar(value=str(self.config.get("largura_mm", 80)))
        largura_combo = ttk.Combobox(opts_frame, textvariable=self._largura_var, values=["80", "58"], width=10, state="readonly")
        largura_combo.grid(row=0, column=1, padx=(5, 0), pady=2, sticky=tk.W)
        ttk.Label(opts_frame, text="mm").grid(row=0, column=2, padx=(3, 0), pady=2, sticky=tk.W)

        self._autostart_var = tk.BooleanVar(value=self.config.get("auto_start", True))
        ttk.Checkbutton(opts_frame, text="Iniciar com Windows", variable=self._autostart_var).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)

        # ─── Botões ───
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Salvar", command=self._salvar).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Cancelar", command=self._root.destroy).pack(side=tk.RIGHT)

        self._root.mainloop()

    def _fazer_login(self):
        """Faz login no backend e salva token."""
        email = self._email_var.get().strip()
        senha = self._senha_var.get().strip()
        server = self._server_var.get().strip()

        if not email or not senha:
            messagebox.showwarning("Aviso", "Informe email e senha")
            return

        self._login_btn.configure(state="disabled")
        self._login_status.set("Conectando...")

        def do_login():
            try:
                client = ApiClient(server, "")
                result = client.login(email, senha)
                if result and (result.get("access_token") or result.get("token")):
                    self.config["token"] = result.get("access_token") or result["token"]
                    self.config["restaurante_id"] = result.get("restaurante", {}).get("id")
                    self.config["server_url"] = server
                    self._root.after(0, lambda: self._login_status.set(
                        f"Conectado! (ID: {self.config['restaurante_id']})"
                    ))
                else:
                    self._root.after(0, lambda: self._login_status.set("Falha no login"))
                    self._root.after(0, lambda: messagebox.showerror("Erro", "Email ou senha incorretos"))
            except Exception as e:
                self._root.after(0, lambda: self._login_status.set(f"Erro: {e}"))
            finally:
                self._root.after(0, lambda: self._login_btn.configure(state="normal"))

        threading.Thread(target=do_login, daemon=True).start()

    def _salvar(self):
        """Salva configurações e fecha."""
        # Impressoras
        for setor, var in self._printer_vars.items():
            val = var.get()
            self.config["impressoras"][setor] = val if val != "(Nenhuma)" else None

        self.config["server_url"] = self._server_var.get().strip()
        self.config["largura_mm"] = int(self._largura_var.get())
        self.config["auto_start"] = self._autostart_var.get()

        save_config(self.config)

        # Auto-start Windows
        if self.config["auto_start"]:
            self._set_autostart(True)
        else:
            self._set_autostart(False)

        if self.on_save:
            self.on_save(self.config)

        messagebox.showinfo("Sucesso", "Configurações salvas!")
        self._root.destroy()

    def _set_autostart(self, enable: bool):
        """Configura/remove auto-start no registro do Windows."""
        import platform
        if platform.system() != "Windows":
            return

        try:
            import winreg
            import sys
            import os
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            if enable:
                if getattr(sys, "frozen", False):
                    exe_path = sys.executable
                else:
                    # Usar o .bat correspondente no diretório pai
                    bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "IMPRESSAO.bat")
                    exe_path = f'"{bat_path}"'
                winreg.SetValueEx(key, "DerekhFoodPrinter", 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, "DerekhFoodPrinter")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning(f"Erro ao configurar auto-start: {e}")

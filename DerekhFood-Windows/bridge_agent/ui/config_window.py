# bridge_agent/ui/config_window.py

"""
Janela de configuração do Bridge Agent (Tkinter).
Login do restaurante + seleção de impressoras + toggle auto-criar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import logging
import threading
import os

from ..config import load_config, save_config
from ..spooler_monitor import listar_impressoras

logger = logging.getLogger("bridge_agent.ui")


class ConfigWindow:
    """Janela principal de configuração do Bridge Agent."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Derekh Food Bridge — Configuração")
        # Tamanho adaptativo: 90% da altura da tela, limitado entre 500 e 700
        screen_h = self.root.winfo_screenheight()
        win_h = min(700, max(500, int(screen_h * 0.85)))
        self.root.geometry(f"520x{win_h}")
        self.root.minsize(480, 500)
        self.root.resizable(True, True)  # permite redimensionar se cortar
        self.root.configure(bg="#1a1a2e")

        # Centraliza na tela
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 520) // 2
        y = max(0, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"+{x}+{y}")

        self.config = load_config()

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background="#1a1a2e")
        style.configure("Dark.TLabel", background="#1a1a2e", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#1a1a2e", foreground="#e94560", font=("Segoe UI", 14, "bold"))
        style.configure("Dark.TEntry", fieldbackground="#16213e", foreground="#e0e0e0")
        style.configure("Dark.TButton", background="#e94560", foreground="white", font=("Segoe UI", 10, "bold"))
        style.configure("Dark.TCheckbutton", background="#1a1a2e", foreground="#e0e0e0", font=("Segoe UI", 9))

        # ─── Frame scrollavel para conteudo (evita corte em telas pequenas) ───
        outer_frame = tk.Frame(self.root, bg="#1a1a2e")
        outer_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer_frame, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main_frame = ttk.Frame(canvas, style="Dark.TFrame", padding=20)
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def _on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Scroll com roda do mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Título
        ttk.Label(main_frame, text="Derekh Food Bridge", style="Title.TLabel").pack(pady=(0, 15))

        # Seção Login
        login_frame = ttk.LabelFrame(main_frame, text="Login do Restaurante", padding=10)
        login_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(login_frame, text="URL do Servidor:").pack(anchor="w")
        self.server_url_var = tk.StringVar(value=self.config.get("server_url", "https://superfood-api.fly.dev"))
        ttk.Entry(login_frame, textvariable=self.server_url_var, width=50).pack(fill="x", pady=(0, 5))

        ttk.Label(login_frame, text="Email:").pack(anchor="w")
        self.email_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.email_var, width=50).pack(fill="x", pady=(0, 5))

        ttk.Label(login_frame, text="Senha:").pack(anchor="w")
        self.senha_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.senha_var, show="*", width=50).pack(fill="x", pady=(0, 5))

        self.login_btn = ttk.Button(login_frame, text="Fazer Login", command=self._do_login)
        self.login_btn.pack(pady=5)

        self.login_status = ttk.Label(login_frame, text="")
        self.login_status.pack()

        # Se já tem token, mostrar status
        if self.config.get("token"):
            self.login_status.config(text="Token salvo (já autenticado)", foreground="#4ecca3")

        # Seção Impressoras
        printer_frame = ttk.LabelFrame(main_frame, text="Impressoras a Monitorar", padding=10)
        printer_frame.pack(fill="x", pady=(0, 10))

        self.printer_vars = {}
        printers = listar_impressoras()
        monitoradas = set(self.config.get("impressoras_monitorar", []))

        if printers:
            for p in printers:
                var = tk.BooleanVar(value=(p in monitoradas))
                self.printer_vars[p] = var
                ttk.Checkbutton(printer_frame, text=p, variable=var).pack(anchor="w")
        else:
            ttk.Label(printer_frame, text="Nenhuma impressora encontrada\n(requer Windows com pywin32)").pack()

        # Opções
        options_frame = ttk.LabelFrame(main_frame, text="Opções", padding=10)
        options_frame.pack(fill="x", pady=(0, 10))

        self.auto_criar_var = tk.BooleanVar(value=self.config.get("auto_criar_pedido", True))
        ttk.Checkbutton(
            options_frame,
            text="Criar pedido automaticamente ao interceptar",
            variable=self.auto_criar_var,
        ).pack(anchor="w")

        ttk.Label(options_frame, text="Prefixo a ignorar (impressões Derekh):").pack(anchor="w", pady=(5, 0))
        self.ignorar_var = tk.StringVar(value=self.config.get("ignorar_prefixo", "Derekh_"))
        ttk.Entry(options_frame, textvariable=self.ignorar_var, width=30).pack(anchor="w")

        ttk.Label(options_frame, text="Codepage da impressora:").pack(anchor="w", pady=(5, 0))
        self.codepage_var = tk.StringVar(value=self.config.get("codepage", "CP860"))
        cp_combo = ttk.Combobox(options_frame, textvariable=self.codepage_var, width=15, state="readonly")
        cp_combo["values"] = ("CP860", "CP850", "UTF-8", "latin-1", "CP437")
        cp_combo.pack(anchor="w")

        self.autostart_var = tk.BooleanVar(value=self.config.get("auto_start", False))
        ttk.Checkbutton(
            options_frame,
            text="Iniciar com Windows",
            variable=self.autostart_var,
        ).pack(anchor="w", pady=(5, 0))

        # Botões
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="Salvar", command=self._save).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="Cancelar", command=self.root.destroy).pack(side="left")

    def _do_login(self):
        """Faz login no servidor e salva o token."""
        email = self.email_var.get().strip()
        senha = self.senha_var.get().strip()
        server_url = self.server_url_var.get().strip().rstrip("/")

        if not email or not senha:
            messagebox.showwarning("Aviso", "Preencha email e senha")
            return

        self.login_btn.config(state="disabled")
        self.login_status.config(text="Conectando...", foreground="#ffd700")

        def do_request():
            try:
                resp = requests.post(
                    f"{server_url}/auth/restaurante/login",
                    json={"email": email, "senha": senha},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Backend retorna 'access_token' (não 'token')
                    token_value = data.get("access_token") or data.get("token")
                    if not token_value:
                        self.root.after(0, lambda: self.login_status.config(
                            text="Erro: resposta sem token",
                            foreground="#e94560"
                        ))
                        return
                    self.config["token"] = token_value
                    self.config["restaurante_id"] = data.get("restaurante", {}).get("id")
                    self.config["server_url"] = server_url
                    # SALVAR IMEDIATAMENTE — sem depender de clicar "Salvar" depois
                    try:
                        save_config(self.config)
                    except Exception as e:
                        logger.error(f"Erro ao salvar config após login: {e}")
                    nome_rest = data.get("restaurante", {}).get("nome", "")
                    self.root.after(0, lambda: self.login_status.config(
                        text=f"Login OK — {nome_rest} (token salvo)",
                        foreground="#4ecca3"
                    ))
                else:
                    self.root.after(0, lambda: self.login_status.config(
                        text=f"Erro: {resp.status_code} — {resp.text[:100]}",
                        foreground="#e94560"
                    ))
            except Exception as e:
                self.root.after(0, lambda: self.login_status.config(
                    text=f"Erro: {str(e)[:80]}",
                    foreground="#e94560"
                ))
            finally:
                self.root.after(0, lambda: self.login_btn.config(state="normal"))

        threading.Thread(target=do_request, daemon=True).start()

    def _save(self):
        """Salva a configuração."""
        self.config["server_url"] = self.server_url_var.get().strip().rstrip("/")
        self.config["impressoras_monitorar"] = [
            name for name, var in self.printer_vars.items() if var.get()
        ]
        self.config["auto_criar_pedido"] = self.auto_criar_var.get()
        self.config["ignorar_prefixo"] = self.ignorar_var.get().strip()
        self.config["codepage"] = self.codepage_var.get()
        self.config["auto_start"] = self.autostart_var.get()

        save_config(self.config)
        self._set_autostart(self.config["auto_start"])
        messagebox.showinfo("Salvo", "Configuração salva com sucesso!")
        self.root.destroy()

    def _set_autostart(self, enable: bool):
        """Configura/remove auto-start no registro do Windows."""
        import platform
        if platform.system() != "Windows":
            return

        try:
            import winreg
            import sys
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            if enable:
                if getattr(sys, "frozen", False):
                    exe_path = f'"{sys.executable}" --silent'
                else:
                    # Usar o .bat correspondente no diretório pai (flag --silent suprime dialog reconfigurar)
                    bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "BRIDGE.bat")
                    exe_path = f'"{bat_path}" --silent'
                winreg.SetValueEx(key, "DerekhFoodBridge", 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, "DerekhFoodBridge")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning(f"Erro ao configurar auto-start: {e}")

    def run(self):
        self.root.mainloop()


def abrir_config():
    """Função utilitária para abrir a janela de configuração."""
    window = ConfigWindow()
    window.run()

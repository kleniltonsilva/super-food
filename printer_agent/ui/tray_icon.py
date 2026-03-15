# printer_agent/ui/tray_icon.py

"""
System Tray icon usando pystray.
Mostra status de conexão e menu de opções.
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("printer_agent.tray")


class TrayIcon:
    """Ícone na bandeja do sistema com menu de contexto."""

    STATUS_COLORS = {
        "conectado": (0, 180, 0),      # Verde
        "desconectado": (200, 0, 0),    # Vermelho
        "imprimindo": (220, 180, 0),    # Amarelo
    }

    def __init__(
        self,
        on_config: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
    ):
        self.on_config = on_config
        self.on_quit = on_quit
        self._status = "desconectado"
        self._icon = None

    def _create_icon_image(self, color: tuple):
        """Cria imagem simples para o ícone (círculo colorido)."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Fundo escuro
            draw.rectangle([0, 0, 63, 63], fill=(40, 40, 40, 255))
            # Círculo de status
            draw.ellipse([16, 16, 48, 48], fill=color + (255,))
            # Letra D
            try:
                draw.text((22, 18), "D", fill=(255, 255, 255, 255))
            except Exception:
                pass
            return img
        except ImportError:
            # Sem Pillow, cria imagem mínima
            from PIL import Image
            return Image.new("RGB", (64, 64), color)

    def _get_menu(self):
        """Cria menu de contexto."""
        import pystray
        items = []

        status_label = {
            "conectado": "Conectado",
            "desconectado": "Desconectado",
            "imprimindo": "Imprimindo...",
        }

        items.append(pystray.MenuItem(
            f"Status: {status_label.get(self._status, self._status)}",
            lambda: None,
            enabled=False,
        ))
        items.append(pystray.Menu.SEPARATOR)

        if self.on_config:
            items.append(pystray.MenuItem("Configurações", lambda: self.on_config()))

        items.append(pystray.Menu.SEPARATOR)

        if self.on_quit:
            items.append(pystray.MenuItem("Sair", lambda: self.on_quit()))

        return pystray.Menu(*items)

    def iniciar(self):
        """Inicia o ícone na bandeja (bloqueante — rodar em thread)."""
        try:
            import pystray
        except ImportError:
            logger.warning("pystray não instalado — tray icon desabilitado")
            return

        color = self.STATUS_COLORS.get(self._status, (128, 128, 128))
        image = self._create_icon_image(color)

        self._icon = pystray.Icon(
            "derekh_food_printer",
            image,
            "Derekh Food - Impressora",
            menu=self._get_menu(),
        )
        self._icon.run()

    def atualizar_status(self, status: str):
        """Atualiza cor e tooltip do ícone."""
        self._status = status
        if self._icon:
            color = self.STATUS_COLORS.get(status, (128, 128, 128))
            self._icon.icon = self._create_icon_image(color)

            status_label = {
                "conectado": "Conectado",
                "desconectado": "Desconectado",
                "imprimindo": "Imprimindo...",
            }
            self._icon.title = f"Derekh Food - {status_label.get(status, status)}"
            self._icon.menu = self._get_menu()

    def parar(self):
        """Para o ícone."""
        if self._icon:
            self._icon.stop()

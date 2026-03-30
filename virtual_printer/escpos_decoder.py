"""
Decodificador ESC/POS → texto legível com anotações de estilo.

Superset do bridge_agent/text_extractor.py — além de extrair texto puro,
também anota comandos de formatação (bold, alinhamento, tamanho, corte).

Três modos de saída:
- decode_text_only()   → texto limpo (como text_extractor.extrair_texto)
- decode_annotated()   → texto com [ANOTAÇÕES] inline
- hex_dump()           → dump hexadecimal estilo xxd
"""

from typing import List, Tuple


# ── Mapa de comandos ESC/POS ─────────────────────────────────────────────────

# ESC (0x1B) commands: ESC + command_byte + params
ESC_COMMANDS = {
    0x40: ("INIT", 0),            # ESC @ — Initialize printer
    0x61: ("ALIGN", 1),           # ESC a n — Set justification (0=L, 1=C, 2=R)
    0x21: ("STYLE", 1),           # ESC ! n — Select print mode (bold, font, etc.)
    0x74: ("CODEPAGE", 1),        # ESC t n — Select character code table
    0x45: ("EMPHASIZE", 1),       # ESC E n — Turn emphasized mode on/off
    0x4D: ("FONT", 1),            # ESC M n — Select character font
    0x64: ("FEED_N", 1),          # ESC d n — Print and feed n lines
    0x4A: ("FEED_DOTS", 1),       # ESC J n — Print and feed n dots
    0x33: ("LINE_SPACING", 1),    # ESC 3 n — Set line spacing to n dots
    0x32: ("LINE_SPACING_DEF", 0),# ESC 2 — Set default line spacing
    0x70: ("PULSE", 2),           # ESC p m t1 t2 — Generate pulse (cash drawer)
    0x63: ("PANEL_BUTTON", 1),    # ESC c 5 n — Enable/disable panel buttons
}

# GS (0x1D) commands
GS_COMMANDS = {
    0x21: ("SIZE", 1),            # GS ! n — Select character size
    0x56: ("CUT", 1),             # GS V m — Select cut mode
    0x42: ("REVERSE", 1),         # GS B n — Turn white/black reverse printing
    0x48: ("HRI_POSITION", 1),    # GS H n — Select HRI character position
    0x66: ("HRI_FONT", 1),       # GS f n — Select font for HRI characters
    0x68: ("BARCODE_HEIGHT", 1),  # GS h n — Set barcode height
    0x77: ("BARCODE_WIDTH", 1),   # GS w n — Set barcode width
    0x6B: ("BARCODE", -1),        # GS k — Print barcode (variable length)
}

ALIGN_NAMES = {0: "LEFT", 1: "CENTER", 2: "RIGHT"}
CUT_NAMES = {0: "FULL", 1: "PARTIAL", 0x41: "PARTIAL", 0x42: "PARTIAL"}
CODEPAGE_NAMES = {0: "CP437", 2: "CP850", 3: "CP860", 19: "CP858", 255: "UTF-8"}
SIZE_NAMES = {
    0x00: "NORMAL",
    0x10: "DOUBLE_W",
    0x01: "DOUBLE_H",
    0x11: "DOUBLE_WH",
}


class ESCPOSDecoder:
    """Decodificador de bytes ESC/POS com anotações de estilo."""

    def __init__(self, codepage: str = "CP860"):
        self.codepage = codepage
        self._fallback_codepages = ["CP860", "UTF-8", "Latin-1", "ASCII"]

    def decode_text_only(self, raw_bytes: bytes) -> str:
        """Extrai apenas o texto legível, removendo todos os comandos ESC/POS."""
        segments = self._parse(raw_bytes)
        lines = []
        for seg_type, content in segments:
            if seg_type == "TEXT":
                lines.append(content)
        text = "".join(lines)
        return self._clean(text)

    def decode_annotated(self, raw_bytes: bytes) -> str:
        """Retorna texto com anotações [COMANDO:VALOR] inline."""
        segments = self._parse(raw_bytes)
        parts = []
        for seg_type, content in segments:
            if seg_type == "TEXT":
                parts.append(content)
            elif seg_type == "CMD":
                parts.append(content)
        text = "".join(parts)
        return self._clean(text)

    def hex_dump(self, raw_bytes: bytes, width: int = 16) -> str:
        """Dump hexadecimal estilo xxd."""
        lines = []
        for offset in range(0, len(raw_bytes), width):
            chunk = raw_bytes[offset:offset + width]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(
                chr(b) if 32 <= b < 127 else "." for b in chunk
            )
            lines.append(f"{offset:08X}  {hex_part:<{width * 3}}  |{ascii_part}|")
        return "\n".join(lines)

    def _parse(self, raw_bytes: bytes) -> List[Tuple[str, str]]:
        """Parseia bytes ESC/POS em segmentos (TEXT, conteúdo) ou (CMD, anotação)."""
        segments: List[Tuple[str, str]] = []
        text_buf = bytearray()
        i = 0
        n = len(raw_bytes)

        while i < n:
            b = raw_bytes[i]

            # ── ESC (0x1B) ────────────────────────────────────────────
            if b == 0x1B and i + 1 < n:
                if text_buf:
                    segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))
                    text_buf.clear()

                cmd_byte = raw_bytes[i + 1]
                cmd_info = ESC_COMMANDS.get(cmd_byte)

                if cmd_info:
                    name, param_count = cmd_info
                    annotation = self._annotate_esc(name, raw_bytes, i + 2, param_count)
                    segments.append(("CMD", annotation))
                    i += 2 + param_count
                else:
                    # Comando desconhecido: pula ESC + 1 byte
                    segments.append(("CMD", f"[ESC:0x{cmd_byte:02X}]"))
                    i += 2

            # ── GS (0x1D) ─────────────────────────────────────────────
            elif b == 0x1D and i + 1 < n:
                if text_buf:
                    segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))
                    text_buf.clear()

                cmd_byte = raw_bytes[i + 1]
                cmd_info = GS_COMMANDS.get(cmd_byte)

                if cmd_info:
                    name, param_count = cmd_info
                    if name == "BARCODE":
                        skip = self._skip_barcode(raw_bytes, i)
                        segments.append(("CMD", "[BARCODE]"))
                        i += skip
                    elif cmd_byte == 0x28:  # GS ( — extended command
                        skip = self._skip_gs_extended(raw_bytes, i)
                        segments.append(("CMD", "[GS_EXT]"))
                        i += skip
                    else:
                        annotation = self._annotate_gs(name, raw_bytes, i + 2, param_count)
                        segments.append(("CMD", annotation))
                        i += 2 + param_count
                elif cmd_byte == 0x28:  # GS ( — extended command (não no mapa)
                    if text_buf:
                        segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))
                        text_buf.clear()
                    skip = self._skip_gs_extended(raw_bytes, i)
                    segments.append(("CMD", "[GS_EXT]"))
                    i += skip
                else:
                    segments.append(("CMD", f"[GS:0x{cmd_byte:02X}]"))
                    i += 2

            # ── FS (0x1C) ─────────────────────────────────────────────
            elif b == 0x1C and i + 1 < n:
                if text_buf:
                    segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))
                    text_buf.clear()
                i += 2  # FS + 1 byte param

            # ── DLE (0x10) ────────────────────────────────────────────
            elif b == 0x10 and i + 1 < n:
                if text_buf:
                    segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))
                    text_buf.clear()
                i += 2  # DLE + 1 byte param

            # ── Controle ignorável ────────────────────────────────────
            elif b < 0x20 and b not in (0x0A, 0x0D, 0x09):
                # Pula bytes de controle (exceto LF, CR, TAB)
                i += 1

            # ── Texto normal ──────────────────────────────────────────
            else:
                text_buf.append(b)
                i += 1

        if text_buf:
            segments.append(("TEXT", self._decode_bytes(bytes(text_buf))))

        return segments

    def _annotate_esc(self, name: str, data: bytes, param_start: int, param_count: int) -> str:
        """Gera anotação para comandos ESC."""
        if param_count == 0:
            return f"[{name}]"

        if param_start >= len(data):
            return f"[{name}]"

        param = data[param_start]

        if name == "ALIGN":
            return f"[ALIGN:{ALIGN_NAMES.get(param, param)}]"
        elif name == "STYLE":
            parts = []
            if param & 0x08:
                parts.append("BOLD:ON")
            else:
                parts.append("BOLD:OFF")
            if param & 0x10:
                parts.append("DOUBLE_H")
            if param & 0x20:
                parts.append("DOUBLE_W")
            return f"[STYLE:{'+'.join(parts)}]" if parts else "[STYLE:NORMAL]"
        elif name == "CODEPAGE":
            return f"[CODEPAGE:{CODEPAGE_NAMES.get(param, f'0x{param:02X}')}]"
        elif name == "EMPHASIZE":
            return f"[BOLD:{'ON' if param else 'OFF'}]"
        else:
            return f"[{name}:{param}]"

    def _annotate_gs(self, name: str, data: bytes, param_start: int, param_count: int) -> str:
        """Gera anotação para comandos GS."""
        if param_count == 0 or param_start >= len(data):
            return f"[{name}]"

        param = data[param_start]

        if name == "SIZE":
            return f"[SIZE:{SIZE_NAMES.get(param, f'0x{param:02X}')}]"
        elif name == "CUT":
            return f"[CUT:{CUT_NAMES.get(param, f'0x{param:02X}')}]"
        else:
            return f"[{name}:{param}]"

    def _skip_barcode(self, data: bytes, pos: int) -> int:
        """Calcula quantos bytes pular para um comando de barcode GS k."""
        if pos + 2 >= len(data):
            return 2
        m = data[pos + 2]
        if m <= 6:
            # Formato A: GS k m d1...dk NUL
            i = pos + 3
            while i < len(data) and data[i] != 0x00:
                i += 1
            return (i + 1) - pos
        else:
            # Formato B: GS k m n d1...dn
            if pos + 3 >= len(data):
                return 3
            n = data[pos + 3]
            return 4 + n

    def _skip_gs_extended(self, data: bytes, pos: int) -> int:
        """Calcula quantos bytes pular para GS ( comandos estendidos."""
        # GS ( fn pL pH ... — pL+pH*256 bytes de dados
        if pos + 4 >= len(data):
            return min(4, len(data) - pos)
        pL = data[pos + 3]
        pH = data[pos + 4]
        length = pL + (pH << 8)
        return 5 + length

    def _decode_bytes(self, raw: bytes) -> str:
        """Decodifica bytes para string com fallback de codepages."""
        for cp in self._fallback_codepages:
            try:
                return raw.decode(cp)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("ascii", errors="replace")

    def _clean(self, text: str) -> str:
        """Remove linhas em branco excessivas e whitespace desnecessário."""
        lines = text.split("\n")
        cleaned = []
        blank_count = 0
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                blank_count += 1
                if blank_count <= 2:
                    cleaned.append("")
            else:
                blank_count = 0
                cleaned.append(stripped)

        # Remove linhas em branco no início e fim
        while cleaned and not cleaned[0]:
            cleaned.pop(0)
        while cleaned and not cleaned[-1]:
            cleaned.pop()

        return "\n".join(cleaned)

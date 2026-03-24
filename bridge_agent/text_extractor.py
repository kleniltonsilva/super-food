# bridge_agent/text_extractor.py

"""
Extrai texto legível de bytes brutos de impressora (ESC/POS ou texto puro).
Remove comandos ESC/POS e decodifica com fallback de codepages.
"""

import re
import logging

logger = logging.getLogger("bridge_agent.text_extractor")

# Bytes de controle ESC/POS que devem ser removidos
ESCPOS_PREFIXES = {
    0x1B,  # ESC
    0x1D,  # GS
    0x1C,  # FS
    0x10,  # DLE
}


def is_escpos(raw_bytes: bytes) -> bool:
    """Detecta se os bytes contêm comandos ESC/POS."""
    for b in raw_bytes[:200]:
        if b in ESCPOS_PREFIXES:
            return True
    return False


def strip_escpos_commands(raw_bytes: bytes) -> bytes:
    """Remove comandos ESC/POS dos bytes, preservando texto imprimível."""
    result = bytearray()
    i = 0
    length = len(raw_bytes)

    while i < length:
        b = raw_bytes[i]

        if b == 0x1B:  # ESC — pula ESC + próximo byte (+ possíveis parâmetros)
            i += 2
            # Alguns comandos ESC têm parâmetros extras
            if i < length and raw_bytes[i - 1] in (0x21, 0x45, 0x47, 0x4D, 0x61):
                i += 1
            continue

        if b == 0x1D:  # GS — pula GS + comando + parâmetros variáveis
            i += 2
            if i < length:
                cmd = raw_bytes[i - 1]
                if cmd in (0x21, 0x42, 0x48, 0x66, 0x68, 0x77):
                    i += 1
                elif cmd == 0x6B:  # GS k — barcode
                    if i < length:
                        n = raw_bytes[i]
                        i += n + 1
                elif cmd == 0x28:  # GS ( — command extenso
                    if i + 1 < length:
                        pL = raw_bytes[i]
                        pH = raw_bytes[i + 1]
                        param_len = pL + (pH << 8)
                        i += 2 + param_len
            continue

        if b == 0x1C:  # FS — pula FS + próximo byte
            i += 2
            continue

        if b == 0x10:  # DLE — pula DLE + próximo byte
            i += 2
            continue

        # Caracteres de controle não-texto (exceto newline, CR, tab)
        if b < 0x20 and b not in (0x0A, 0x0D, 0x09):
            i += 1
            continue

        result.append(b)
        i += 1

    return bytes(result)


def decode_text(raw_bytes: bytes, codepage: str = "CP860") -> str:
    """Decodifica bytes com fallback de codepages."""
    codepages = [codepage, "utf-8", "latin-1", "ascii"]
    for cp in codepages:
        try:
            return raw_bytes.decode(cp, errors="replace")
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode("ascii", errors="replace")


def clean_text(text: str) -> str:
    """Limpa texto extraído: remove linhas vazias excessivas, whitespace residual."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.rstrip()
        # Remove linhas que são apenas separadores
        if line and not re.match(r"^[-=_*]{3,}$", line.strip()):
            cleaned.append(line)
        elif not line and cleaned and cleaned[-1]:
            cleaned.append("")  # Preserva 1 linha vazia entre blocos

    # Remove linhas vazias no início e fim
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return "\n".join(cleaned)


def extrair_texto(raw_bytes: bytes, codepage: str = "CP860") -> str:
    """Pipeline completo: detecta ESC/POS → strip → decode → clean."""
    if is_escpos(raw_bytes):
        logger.debug("Detectado ESC/POS — removendo comandos")
        raw_bytes = strip_escpos_commands(raw_bytes)

    text = decode_text(raw_bytes, codepage)
    text = clean_text(text)
    logger.info(f"Texto extraído: {len(text)} chars")
    return text

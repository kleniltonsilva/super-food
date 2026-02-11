# backend/app/routers/upload.py

"""
Router de Upload de Imagens
Aceita upload de arquivos, redimensiona com Pillow e salva localmente.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image, ImageOps
import uuid
import os
from pathlib import Path
from io import BytesIO

router = APIRouter(prefix="/api/upload", tags=["Upload"])

# Diretório base para uploads
UPLOAD_DIR = Path("backend/static/uploads")

# Configurações por tipo de imagem
TIPO_CONFIG = {
    "logo": {"max_size": (200, 200), "mode": "thumbnail"},
    "banner": {"max_size": (1200, 400), "mode": "fit"},
    "produto": {"max_size": (600, 600), "mode": "thumbnail"},
    "combo": {"max_size": (600, 400), "mode": "fit"},
    "categoria": {"max_size": (400, 400), "mode": "thumbnail"},
}

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/imagem")
async def upload_imagem(
    arquivo: UploadFile = File(...),
    tipo: str = Form(...),
    restaurante_id: int = Form(...),
):
    """
    Upload e processamento de imagem.

    Args:
        arquivo: Arquivo de imagem (jpg, png, webp)
        tipo: Tipo da imagem (logo, banner, produto, combo, categoria)
        restaurante_id: ID do restaurante (multi-tenant)

    Returns:
        {"url": "/static/uploads/{restaurante_id}/tipo_uuid.webp"}
    """
    # Validar tipo
    if tipo not in TIPO_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Use: {', '.join(TIPO_CONFIG.keys())}"
        )

    # Validar content type
    if arquivo.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Use: JPG, PNG ou WebP"
        )

    # Ler arquivo
    conteudo = await arquivo.read()

    # Validar tamanho
    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Arquivo muito grande. Máximo: 5MB"
        )

    # Processar imagem com Pillow
    try:
        img = Image.open(BytesIO(conteudo))
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida")

    # Converter para RGB se necessário (ex: PNG com transparência)
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    config = TIPO_CONFIG[tipo]
    max_size = config["max_size"]

    if config["mode"] == "fit":
        # Crop centralizado para preencher dimensão exata
        img = ImageOps.fit(img, max_size, method=Image.LANCZOS)
    else:
        # Thumbnail mantém aspect ratio
        img.thumbnail(max_size, Image.LANCZOS)

    # Criar diretório do restaurante
    dest_dir = UPLOAD_DIR / str(restaurante_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Gerar nome único
    filename = f"{tipo}_{uuid.uuid4().hex[:12]}.webp"
    filepath = dest_dir / filename

    # Salvar como WebP (melhor compressão)
    img.save(str(filepath), "WEBP", quality=85)

    # URL relativa para servir via /static
    url = f"/static/uploads/{restaurante_id}/{filename}"

    return {"url": url, "filename": filename}

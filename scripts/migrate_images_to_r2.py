#!/usr/bin/env python3
# scripts/migrate_images_to_r2.py

"""
Migra imagens do filesystem local para Cloudflare R2
Uso: python scripts/migrate_images_to_r2.py [--dry-run]
"""

import os
import sys
import argparse
import mimetypes
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
from database.models import Produto, SiteConfig, Combo


def main():
    parser = argparse.ArgumentParser(description="Migra imagens para Cloudflare R2")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem executar")
    args = parser.parse_args()

    # Verifica config R2
    r2_endpoint = os.getenv("R2_ENDPOINT")
    r2_key = os.getenv("R2_ACCESS_KEY_ID")
    r2_secret = os.getenv("R2_SECRET_ACCESS_KEY")
    r2_bucket = os.getenv("R2_BUCKET_NAME", "superfood-uploads")
    cdn_url = os.getenv("CDN_URL", "").rstrip("/")

    if not all([r2_endpoint, r2_key, r2_secret]) and not args.dry_run:
        print("ERRO: Configure R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY no .env")
        sys.exit(1)

    # Conecta ao banco
    db_url = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Scan diretorio de uploads
    upload_dir = Path("backend/static/uploads")
    if not upload_dir.exists():
        print("Diretorio de uploads nao encontrado")
        return

    files = list(upload_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    print(f"Encontrados {len(files)} arquivos para migrar")

    if not args.dry_run:
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_key,
            aws_secret_access_key=r2_secret,
            region_name="auto",
        )

    uploaded = 0
    errors = 0

    for filepath in files:
        # Key relativo: "1/logo_abc123.webp"
        key = str(filepath.relative_to(upload_dir))
        content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"

        if args.dry_run:
            print(f"  [DRY-RUN] Upload: {key} ({content_type})")
            uploaded += 1
            continue

        try:
            s3.upload_file(
                str(filepath),
                r2_bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
            uploaded += 1
            print(f"  Uploaded: {key}")
        except Exception as e:
            errors += 1
            print(f"  ERRO: {key} - {e}")

    print(f"\nUpload concluido: {uploaded} OK, {errors} erros")

    if args.dry_run:
        print("\n[DRY-RUN] Nenhuma alteracao no banco. Execute sem --dry-run para aplicar.")
        db.close()
        return

    # Atualiza URLs no banco
    old_prefix = "/static/uploads/"
    new_prefix = f"{cdn_url}/" if cdn_url else f"https://{r2_bucket}.r2.cloudflarestorage.com/"

    print(f"\nAtualizando URLs no banco: {old_prefix} -> {new_prefix}")

    # Produtos
    produtos = db.query(Produto).filter(Produto.imagem_url.like(f"{old_prefix}%")).all()
    for p in produtos:
        p.imagem_url = p.imagem_url.replace(old_prefix, new_prefix)
    print(f"  Produtos atualizados: {len(produtos)}")

    # SiteConfig (logo, banner)
    sites = db.query(SiteConfig).all()
    site_count = 0
    for s in sites:
        changed = False
        if s.logo_url and s.logo_url.startswith(old_prefix):
            s.logo_url = s.logo_url.replace(old_prefix, new_prefix)
            changed = True
        if s.banner_principal_url and s.banner_principal_url.startswith(old_prefix):
            s.banner_principal_url = s.banner_principal_url.replace(old_prefix, new_prefix)
            changed = True
        if changed:
            site_count += 1
    print(f"  SiteConfigs atualizados: {site_count}")

    # Combos
    combos = db.query(Combo).filter(Combo.imagem_url.like(f"{old_prefix}%")).all()
    for c in combos:
        c.imagem_url = c.imagem_url.replace(old_prefix, new_prefix)
    print(f"  Combos atualizados: {len(combos)}")

    db.commit()
    db.close()

    print("\nMigracao concluida! Arquivos locais mantidos como backup.")
    print("Para limpar: rm -rf backend/static/uploads/*")


if __name__ == "__main__":
    main()

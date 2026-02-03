"""
Seed: Criar super administrador padrão.

Super Food SaaS - Sistema de Inicialização de Dados
"""

import os
from typing import Optional
from database.seed.base_seed import BaseSeed
from database.models import SuperAdmin


class SuperAdminSeed(BaseSeed):
    """Cria o super administrador padrão do sistema."""

    order = 1
    name = "Super Admin Padrão"
    skip_if_exists = True

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """Verifica se já existe um super admin com o usuário padrão."""
        usuario = os.getenv("SUPER_ADMIN_USER", "superadmin")
        return session.query(SuperAdmin).filter(
            SuperAdmin.usuario == usuario
        ).first() is not None

    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """Cria o super admin padrão se não existir."""
        if self.skip_if_exists and self.check_exists(session):
            return 0

        usuario = os.getenv("SUPER_ADMIN_USER", "superadmin")
        senha = os.getenv("SUPER_ADMIN_PASS", "SuperFood2025!")
        email = os.getenv("SUPER_ADMIN_EMAIL", "admin@superfood.com.br")

        admin = SuperAdmin(
            usuario=usuario,
            email=email,
            ativo=True
        )
        admin.set_senha(senha)

        session.add(admin)
        session.commit()
        return 1


# Instância do seed para registro
seed = SuperAdminSeed()

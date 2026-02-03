"""
Classe base abstrata para todos os scripts de seed.
Garante consistência e facilita adição de novos seeds.

Super Food SaaS - Sistema de Inicialização de Dados
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseSeed(ABC):
    """
    Classe base para seeds do banco de dados.

    Todos os seeds devem herdar desta classe e implementar
    o método run() e opcionalmente check_exists().

    Atributos:
        order (int): Ordem de execução (menor = primeiro)
        name (str): Nome descritivo do seed
        skip_if_exists (bool): Se True, pula se dados já existirem
    """

    # Ordem de execução (menor = primeiro)
    order: int = 100

    # Nome descritivo do seed
    name: str = "Base Seed"

    # Se True, só executa se dados não existirem
    skip_if_exists: bool = True

    @abstractmethod
    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """
        Executa o seed.

        Args:
            session: Sessão SQLAlchemy ativa
            restaurante_id: ID do restaurante (para seeds multi-tenant)

        Returns:
            Número de registros criados
        """
        pass

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """
        Verifica se dados já existem (para skip_if_exists).

        Args:
            session: Sessão SQLAlchemy ativa
            restaurante_id: ID do restaurante (para seeds multi-tenant)

        Returns:
            True se dados já existem, False caso contrário
        """
        return False

    def __repr__(self) -> str:
        return f"<Seed: {self.name} (order={self.order})>"

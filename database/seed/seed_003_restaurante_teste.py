"""
Seed: Criar restaurante de teste para desenvolvimento.

Derekh Food SaaS - Sistema de Inicialização de Dados
"""

from datetime import datetime, timedelta
from typing import Optional
from database.seed.base_seed import BaseSeed
from database.models import Restaurante, ConfigRestaurante


class RestauranteTesteSeed(BaseSeed):
    """Cria restaurante de teste para desenvolvimento."""

    order = 3
    name = "Restaurante de Teste"
    skip_if_exists = True

    # Dados do restaurante de teste
    EMAIL_TESTE = "teste@superfood.com"
    SENHA_TESTE = "123456"

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """Verifica se o restaurante de teste já existe."""
        return session.query(Restaurante).filter(
            Restaurante.email == self.EMAIL_TESTE
        ).first() is not None

    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """Cria restaurante de teste com configuração completa."""
        if self.skip_if_exists and self.check_exists(session):
            return 0

        # Criar restaurante
        restaurante = Restaurante(
            nome='Restaurante Teste',
            nome_fantasia='Teste Burguer',
            email=self.EMAIL_TESTE,
            telefone='11999999999',
            endereco_completo='Rua Teste, 123, Centro, São Paulo, SP, 01310-100',
            cidade='São Paulo',
            estado='SP',
            cep='01310-100',
            latitude=-23.550520,
            longitude=-46.633308,
            plano='premium',
            valor_plano=599.90,
            limite_motoboys=999,
            ativo=True,
            status='ativo',
            data_vencimento=datetime.now() + timedelta(days=365)
        )

        restaurante.set_senha(self.SENHA_TESTE)
        restaurante.gerar_codigo_acesso()

        session.add(restaurante)
        session.flush()  # Obtém o ID antes do commit

        # Criar configuração do restaurante
        config = ConfigRestaurante(
            restaurante_id=restaurante.id,
            status_atual='fechado',
            modo_despacho='auto_economico',

            # Configurações de entrega
            raio_entrega_km=15.0,
            tempo_medio_preparo=30,
            despacho_automatico=True,

            # Taxa de entrega (para o cliente)
            taxa_entrega_base=5.00,
            distancia_base_km=3.0,
            taxa_km_extra=1.50,

            # Pagamento do motoboy
            valor_base_motoboy=5.00,
            valor_km_extra_motoboy=1.00,
            taxa_diaria=50.0,
            valor_lanche=15.0,

            # Configurações de rota
            max_pedidos_por_rota=5,
            permitir_ver_saldo_motoboy=True,

            # Horários
            horario_abertura='18:00',
            horario_fechamento='23:00',
            dias_semana_abertos='seg,ter,qua,qui,sex,sab,dom'
        )

        session.add(config)
        session.commit()

        return 1

    def get_credenciais(self) -> dict:
        """Retorna as credenciais do restaurante de teste."""
        return {
            'email': self.EMAIL_TESTE,
            'senha': self.SENHA_TESTE
        }


# Instância do seed para registro
seed = RestauranteTesteSeed()

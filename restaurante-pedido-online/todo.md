# Restaurante Pedido Online - TODO

## Funcionalidades Obrigatórias

### Cardápio Digital
- [x] Schema de banco de dados para produtos, categorias e variações
- [x] Procedures tRPC para listar categorias e produtos
- [x] Interface de cardápio com categorias (Promoções, Pizzas Tradicionais, Pizza Napolitana, Pizza Quadrada, Calzones, Bebidas)
- [x] Cards de produtos com imagens, descrições e preços
- [x] Filtros e busca de produtos
- [x] Modal/página de detalhes do produto

### Carrinho de Compras
- [x] Schema de banco de dados para carrinho e itens do carrinho
- [x] Procedures tRPC para adicionar/remover/atualizar itens do carrinho
- [x] Interface do carrinho com visualização de itens
- [x] Cálculo automático de total
- [x] Persistência do carrinho (localStorage ou banco de dados)

### Montagem Personalizada de Pizzas
- [x] Schema para sabores e opções de personalização
- [x] Procedures tRPC para obter sabores e validar seleções
- [x] Interface de montagem de pizza com seleção de até 4 sabores
- [x] Seleção de tamanhos diferentes
- [x] Cálculo dinâmico de preço baseado em sabores e tamanho

### Sistema de Checkout
- [x] Schema para pedidos e endereços de entrega
- [x] Procedures tRPC para criar pedidos
- [x] Interface de checkout com resumo do pedido
- [x] Seleção de forma de pagamento (Dinheiro, Cartão Crédito/Débito, PIX, Voucher)
- [x] Opção de entrega ou retirada
- [x] Validação de dados antes de confirmar pedido

### Gestão de Endereços
- [x] Schema para endereços de entrega
- [x] Procedures tRPC para CRUD de endereços
- [x] Validação de bairros atendidos
- [x] Cálculo de tempo estimado de entrega
- [x] Interface para adicionar/editar/selecionar endereços

### Programa de Fidelidade
- [x] Schema para pontos de fidelidade dos usuários
- [x] Procedures tRPC para acumular e usar pontos
- [x] Interface para visualizar saldo de pontos
- [x] Catálogo de prêmios resgatáveis
- [x] Lógica de acúmulo de pontos por pedido

### Painel Administrativo
- [ ] Autenticação e controle de acesso para admin
- [ ] Interface para gerenciar categorias
- [ ] Interface para gerenciar produtos (CRUD)
- [ ] Interface para gerenciar preços e promoções
- [ ] Interface para visualizar e gerenciar pedidos
- [ ] Dashboard com estatísticas de vendas
- [ ] Procedures tRPC para operações administrativas

### Sistema de Pedidos em Tempo Real
- [x] Schema para armazenar histórico de pedidos
- [x] Procedures tRPC para criar e atualizar status de pedidos
- [x] Notificação ao proprietário quando novo pedido é realizado
- [ ] Atualização em tempo real do status do pedido para cliente
- [x] Interface para rastrear pedido

### Upsell de Bebidas
- [ ] Lógica para sugerir bebidas durante checkout
- [ ] Interface de upsell com bebidas recomendadas
- [ ] Adição rápida de bebidas ao carrinho

### Design e Responsividade
- [ ] Design moderno inspirado no Expresso Delivery
- [ ] Paleta de cores e tipografia
- [ ] Layout responsivo para mobile
- [ ] Layout responsivo para desktop
- [ ] Testes de usabilidade em diferentes dispositivos

## Tarefas Técnicas

- [ ] Configurar schema do banco de dados
- [ ] Implementar procedures tRPC básicas
- [ ] Configurar autenticação de usuário
- [ ] Implementar sistema de notificações
- [ ] Testes unitários com Vitest
- [ ] Otimização de performance
- [ ] Tratamento de erros e validações

## Melhorias Futuras

- [ ] Integração com gateway de pagamento (Stripe)
- [ ] App mobile nativo
- [ ] Sistema de avaliações e comentários
- [ ] Histórico de pedidos do usuário
- [ ] Cupons e códigos promocionais
- [ ] Integração com WhatsApp
- [ ] Sistema de agendamento de pedidos

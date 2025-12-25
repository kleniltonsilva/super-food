Documentação Técnica - Gerenciador de Pagamento para Motoboys

## Visão Geral do Projeto

O **Gerenciador de Motoboys** é uma aplicação desktop desenvolvida em Python que automatiza o cálculo diário de pagamento de motoboys em restaurantes de delivery.  

O principal objetivo é eliminar cálculos manuais propensos a erros e garantir um pagamento justo baseado na **distância real percorrida** em cada entrega, utilizando a API do Mapbox para obter rotas precisas.

O sistema permite:
- Cadastro e gerenciamento de motoboys
- Configuração flexível de taxas (diária, lanche, entrega base, km extra)
- Registro de entregas com endereço e código da comanda
- Cálculo automático com progresso visual
- Persistência de histórico em banco local
- Consulta de resultados por data/comanda
- Ranking histórico de desempenho dos motoboys

## Arquitetura e Tecnologias

- **Linguagem**: Python 3.x
- **Interface gráfica**: Tkinter (nativo do Python)
- **Banco de dados**: SQLite (arquivo local `motoboy.db`)
- **Requisições HTTP**: Biblioteca `requests`
- **API externa**: Mapbox Geocoding + Directions API (cálculo de distância e tempo real)
- **Outras**: `os`, `datetime`, `urllib.parse`, `sqlite3`, `tkinter.ttk`

O projeto está contido em um único arquivo (`main.py`) para simplicidade, mas com separação lógica clara:
- Funções de integração com Mapbox
- Classe `DBManager` para operações no banco
- Classe `App` para lógica da interface e fluxo da aplicação

## Estrutura do Banco de Dados (SQLite)

### Tabela `config`
Armazena configurações globais (uma única linha).

| Coluna                | Tipo    | Descrição                              |
|-----------------------|---------|----------------------------------------|
| id                    | INTEGER | Chave primária                         |
| restaurant_address    | TEXT    | Endereço do restaurante                |
| daily_rate            | REAL    | Taxa diária fixa (R$)                  |
| lanche_value          | REAL    | Valor do lanche (R$)                    |
| base_delivery_fee     | REAL    | Taxa base por entrega (até limite km)  |
| distance_threshold    | REAL    | Limite de km para taxa base            |
| extra_rate            | REAL    | Valor extra por km acima do limite     |

### Tabela `motoboys`
Lista de motoboys cadastrados.

| Coluna | Tipo    | Descrição         |
|--------|---------|-------------------|
| id     | INTEGER | Chave primária    |
| name   | TEXT    | Nome (único)      |

### Tabela `results`
Histórico de cálculos diários.

| Coluna       | Tipo    | Descrição                                      |
|--------------|---------|------------------------------------------------|
| id           | INTEGER | Chave primária                                 |
| motoboy_name | TEXT    | Nome do motoboy                                |
| result       | REAL    | Valor total pago (diária + lanche + entregas)  |
| deliveries   | INTEGER | Número de entregas no dia                      |
| taxas        | REAL    | Total ganho apenas com taxas de entrega        |
| date         | TEXT    | Data/hora do cálculo                           |
| details      | TEXT    | Detalhes de cada entrega (endereço, distância, valor) |

## Fluxo Principal de Uso

1. **Cadastro de motoboys** → Tela inicial → "Cadastrar Motoboys"
2. **Seleção de motoboys para pagamento** → "Pagar Motoboys"
3. **Configuração do dia** → Endereço do restaurante + taxas
4. **Registro de entregas** → Para cada motoboy: quantidade → endereços + comandas
5. **Cálculo automático** → Integração com Mapbox → barra de progresso → exibição do resultado
6. **Salvamento** → Dados inseridos na tabela `results`
7. **Consulta/Ranking** → Telas dedicadas para histórico e desempenho acumulado

## Cálculo do Pagamento
Valor por entrega =
base_delivery_fee                                   se distância ≤ distance_threshold
base_delivery_fee + (distância - distance_threshold) × extra_rate   caso contrário
Total de taxas = soma de todas as entregas
Pagamento final = daily_rate + lanche_value + Total de taxas
textA distância é obtida em tempo real via Mapbox Directions API (não estimativa manual).

## Integração com Mapbox API

- **Geocodificação**: Converte endereço em coordenadas (longitude, latitude)
- **Direções**: Obtém rota completa entre restaurante e destino
- **Tratamento de erros**: Timeout, endereço não encontrado, falha de rede → valor padrão 0 para evitar travamento

## Ranking de Desempenho

Consulta SQL utilizada:

```sql
SELECT 
    motoboy_name,
    SUM(deliveries) AS total_deliveries,
    SUM(taxas) AS total_taxas,
    SUM(result) AS total_final
FROM results
GROUP BY motoboy_name
ORDER BY total_deliveries DESC
LIMIT 50
Exibe posição, nome, total de entregas, valor ganho com taxas e valor total pago (acumulado histórico).
Desafios Enfrentados e Soluções Implementadas

Ranking inicialmente mostrava apenas o último dia
→ Solução: Adição de colunas deliveries e taxas + migração automática de schema + consulta com agregação SUM e GROUP BY.
Travamento da interface durante cálculo de rotas
→ Solução: Tela de carregamento com barra de progresso e timer, atualizada via after().
Falhas na API Mapbox (endereços inválidos ou rede)
→ Tratamento de exceções + fallback para distância 0 + logs de erro.
Persistência segura de configurações e dados antigos
→ Migração de schema automática (alter_schema()) para adicionar colunas sem perda de dados.
Compatibilidade ao gerar executável (.exe)
→ Uso de os.path.dirname(os.path.abspath(__file__)) para localizar imagem corretamente.

Possíveis Melhorias Futuras

Exportação de relatórios (PDF/Excel)
Suporte a múltiplos restaurantes
Aplicativo móvel complementar para motoboys registrarem entregas
Cache local avançado de rotas para reduzir chamadas à API
Autenticação e controle de acesso
Dashboard web com gráficos de desempenho

Conclusão
Este projeto demonstra habilidades práticas em:

Desenvolvimento de aplicações desktop completas
Integração com APIs externas
Modelagem e persistência de dados
Tratamento robusto de erros
Interface amigável e experiência do usuário
Resolução de problemas reais de pequenos negócios

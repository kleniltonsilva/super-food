# Gerenciador de Pagamento para Motoboys 🚀

Um sistema desktop completo em **Python** para gerenciar entregas de motoboys em restaurantes, calcular pagamentos automaticamente com base em distância real (via Mapbox API), cadastrar motoboys, salvar histórico e gerar **ranking de desempenho**.

Projeto desenvolvido com foco em resolver um problema real de pequenos e médios restaurantes: calcular de forma justa e precisa quanto cada motoboy deve receber por dia.

<img src="foto.png" alt="Tela principal do sistema" width="600"/>

## ✨ Principais Funcionalidades

- Cadastro e exclusão de motoboys
- Configuração flexível: taxa diária, lanche, taxa base por entrega, limite de km e valor extra por km
- Integração com **Mapbox API** para cálculo real de distância e tempo de rota (não estimativa manual!)
- Registro de entregas com código da comanda
- Cálculo automático do pagamento por motoboy (diária + lanche + valor por entrega)
- Histórico completo salvo em banco SQLite
- Pesquisa por data e código da comanda
- **Ranking geral** de motoboys por número de entregas e valor total ganho
- Interface gráfica intuitiva com Tkinter

## 🚀 Tecnologias Utilizadas

- **Python 3**
- **Tkinter** (interface gráfica nativa)
- **SQLite** (banco de dados local leve)
- **Requests** (integração com API externa)
- **Mapbox Geocoding + Directions API** (cálculo preciso de rotas)

## 🛠️ Como Executar

1. Clone o repositório:
```bash
git clone https://github.com/kleniltonsilva/gerenciador-motoboys.git

cd gerenciador-motoboys
## 👨‍💻 Sobre o Desenvolvedor
Desenvolvedor Python em busca de oportunidades júnior. Este projeto resolveu um problema real de um restaurante conhecido.

🔗 LinkedIn: https://www.linkedin.com/in/klenilton-silva-25588834b/
📧 kdkeforever@gmail.com
Whatsaap: +351 933358929


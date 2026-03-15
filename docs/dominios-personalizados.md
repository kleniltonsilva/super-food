# Dominios Personalizados - Derekh Food

## Como funciona

Cada restaurante pode ter seu proprio dominio (ex: `pedidos.minhapizzaria.com.br`)
alem do subdominio padrao `minhapizzaria.superfood.com.br`.

## Passo a passo para o restaurante

### 1. Adicionar dominio no painel

No painel admin do restaurante:
- Va em **Configuracoes > Dominios**
- Clique em **Adicionar Dominio**
- Digite o dominio desejado (ex: `pedidos.minhapizzaria.com.br`)

### 2. Configurar DNS

No painel do seu provedor de dominio (Registro.br, GoDaddy, Cloudflare, etc.):

- Crie um registro **CNAME** apontando para `proxy.superfood.com.br`

| Tipo  | Nome     | Valor                     | TTL  |
|-------|----------|---------------------------|------|
| CNAME | pedidos  | proxy.superfood.com.br    | 3600 |

### 3. Verificar DNS

- Volte ao painel e clique em **Verificar DNS**
- O sistema verifica se o CNAME esta configurado corretamente
- Apos verificacao, o SSL e ativado automaticamente (pode levar ate 5 minutos)

### 4. Pronto!

Seu site estara acessivel em `https://pedidos.minhapizzaria.com.br`

## Notas tecnicas

- SSL e provido automaticamente via Caddy (Let's Encrypt)
- O dominio personalizado funciona em paralelo com o subdominio `.superfood.com.br`
- Propagacao DNS pode levar ate 48 horas (geralmente 1-2 horas)
- Dominios `.com.br` devem ser registrados no Registro.br

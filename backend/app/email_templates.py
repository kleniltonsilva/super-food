# backend/app/email_templates.py
"""
Templates HTML para emails transacionais do Derekh Food.
"""


def gerar_email_boas_vindas(
    nome_fantasia: str,
    codigo_acesso: str,
    senha_padrao: str,
    link_painel: str,
    link_onboarding: str,
) -> tuple[str, str]:
    """Retorna (assunto, html) do email de boas-vindas."""
    assunto = f"Bem-vindo ao Derekh Food, {nome_fantasia}!"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f5;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#f59e0b,#d97706);padding:32px 40px;text-align:center;">
          <h1 style="color:#ffffff;font-size:24px;margin:0;">Derekh Food</h1>
          <p style="color:#fef3c7;font-size:14px;margin:8px 0 0;">Sistema de Delivery Inteligente</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <h2 style="color:#18181b;font-size:20px;margin:0 0 16px;">Bem-vindo, {nome_fantasia}!</h2>
          <p style="color:#52525b;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Seu restaurante foi cadastrado com sucesso no Derekh Food. Abaixo estao suas credenciais de acesso ao painel administrativo.
          </p>

          <!-- Credenciais -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;margin-bottom:24px;">
            <tr><td style="padding:20px;">
              <p style="color:#92400e;font-size:13px;font-weight:600;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">Suas Credenciais</p>
              <table role="presentation" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="color:#78716c;font-size:14px;padding:4px 16px 4px 0;">Codigo de Acesso:</td>
                  <td style="color:#18181b;font-size:16px;font-weight:700;font-family:monospace;letter-spacing:1px;">{codigo_acesso}</td>
                </tr>
                <tr>
                  <td style="color:#78716c;font-size:14px;padding:4px 16px 4px 0;">Senha:</td>
                  <td style="color:#18181b;font-size:16px;font-weight:700;font-family:monospace;">{senha_padrao}</td>
                </tr>
              </table>
              <p style="color:#a16207;font-size:12px;margin:12px 0 0;">Recomendamos alterar sua senha apos o primeiro acesso.</p>
            </td></tr>
          </table>

          <!-- Botoes CTA -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
            <tr>
              <td align="center" style="padding:0 4px;">
                <a href="{link_painel}" style="display:inline-block;background:#f59e0b;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;padding:12px 28px;border-radius:8px;">
                  Acessar Painel
                </a>
              </td>
              <td align="center" style="padding:0 4px;">
                <a href="{link_onboarding}" style="display:inline-block;background:#18181b;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;padding:12px 28px;border-radius:8px;">
                  Guia de Inicio
                </a>
              </td>
            </tr>
          </table>

          <!-- Checklist -->
          <p style="color:#18181b;font-size:15px;font-weight:600;margin:0 0 12px;">Proximos passos:</p>
          <table role="presentation" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
            <tr><td style="color:#52525b;font-size:14px;padding:4px 0;">1. Acesse o painel e configure os dados do restaurante</td></tr>
            <tr><td style="color:#52525b;font-size:14px;padding:4px 0;">2. Adicione categorias e produtos ao cardapio</td></tr>
            <tr><td style="color:#52525b;font-size:14px;padding:4px 0;">3. Defina areas de entrega e bairros</td></tr>
            <tr><td style="color:#52525b;font-size:14px;padding:4px 0;">4. Instale os apps (Motoboy, KDS, Garcom) nos celulares</td></tr>
            <tr><td style="color:#52525b;font-size:14px;padding:4px 0;">5. Faca um pedido de teste para validar o fluxo</td></tr>
          </table>

          <p style="color:#a1a1aa;font-size:13px;margin:0;">
            Duvidas? Fale conosco pelo WhatsApp ou responda este email.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#fafafa;padding:20px 40px;text-align:center;border-top:1px solid #e4e4e7;">
          <p style="color:#a1a1aa;font-size:12px;margin:0;">
            Derekh Food — Sistema de Delivery Inteligente<br>
            Este email foi enviado automaticamente. Nao responda diretamente.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return assunto, html


def gerar_email_verificacao(nome: str, codigo: str) -> tuple[str, str]:
    """Retorna (assunto, html) do email de verificação de conta."""
    assunto = "Seu código de verificação - Derekh Food"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f5;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#f59e0b,#d97706);padding:32px 40px;text-align:center;">
          <h1 style="color:#ffffff;font-size:24px;margin:0;">Derekh Food</h1>
          <p style="color:#fef3c7;font-size:14px;margin:8px 0 0;">Verificação de Email</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <h2 style="color:#18181b;font-size:20px;margin:0 0 16px;">Olá, {nome}!</h2>
          <p style="color:#52525b;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Use o código abaixo para verificar seu email. Ele é válido por <strong>10 minutos</strong>.
          </p>

          <!-- Código OTP -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
            <tr><td align="center">
              <div style="display:inline-block;background:#fefce8;border:2px solid #fde68a;border-radius:12px;padding:20px 40px;">
                <span style="font-family:monospace;font-size:36px;font-weight:700;letter-spacing:8px;color:#92400e;">{codigo}</span>
              </div>
            </td></tr>
          </table>

          <p style="color:#a1a1aa;font-size:13px;margin:0;text-align:center;">
            Se você não criou uma conta, ignore este email.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#fafafa;padding:20px 40px;text-align:center;border-top:1px solid #e4e4e7;">
          <p style="color:#a1a1aa;font-size:12px;margin:0;">
            Derekh Food — Sistema de Delivery Inteligente<br>
            Este email foi enviado automaticamente.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return assunto, html


def gerar_email_reset_senha(nome: str, codigo: str) -> tuple[str, str]:
    """Retorna (assunto, html) do email de redefinição de senha."""
    assunto = "Redefinição de senha - Derekh Food"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f5;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#ef4444,#dc2626);padding:32px 40px;text-align:center;">
          <h1 style="color:#ffffff;font-size:24px;margin:0;">Derekh Food</h1>
          <p style="color:#fecaca;font-size:14px;margin:8px 0 0;">Redefinição de Senha</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <h2 style="color:#18181b;font-size:20px;margin:0 0 16px;">Olá, {nome}!</h2>
          <p style="color:#52525b;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Recebemos uma solicitação para redefinir sua senha. Use o código abaixo. Ele é válido por <strong>10 minutos</strong>.
          </p>

          <!-- Código OTP -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
            <tr><td align="center">
              <div style="display:inline-block;background:#fef2f2;border:2px solid #fecaca;border-radius:12px;padding:20px 40px;">
                <span style="font-family:monospace;font-size:36px;font-weight:700;letter-spacing:8px;color:#991b1b;">{codigo}</span>
              </div>
            </td></tr>
          </table>

          <p style="color:#a1a1aa;font-size:13px;margin:0;text-align:center;">
            Se você não solicitou a redefinição de senha, ignore este email. Sua senha permanecerá a mesma.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#fafafa;padding:20px 40px;text-align:center;border-top:1px solid #e4e4e7;">
          <p style="color:#a1a1aa;font-size:12px;margin:0;">
            Derekh Food — Sistema de Delivery Inteligente<br>
            Este email foi enviado automaticamente.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return assunto, html


def gerar_email_lembrete_cupom(
    nome: str,
    codigo_cupom: str,
    desconto: str,
    expira: str,
    nome_restaurante: str,
) -> tuple[str, str]:
    """Retorna (assunto, html) do email de lembrete de cupom expirando."""
    assunto = f"Seu cupom expira amanhã! - {nome_restaurante}"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f5;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#f59e0b,#d97706);padding:32px 40px;text-align:center;">
          <h1 style="color:#ffffff;font-size:24px;margin:0;">{nome_restaurante}</h1>
          <p style="color:#fef3c7;font-size:14px;margin:8px 0 0;">Não perca seu desconto!</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <h2 style="color:#18181b;font-size:20px;margin:0 0 16px;">Olá, {nome}!</h2>
          <p style="color:#52525b;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Seu cupom exclusivo expira amanhã! Não deixe passar essa oportunidade.
          </p>

          <!-- Cupom destaque -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fefce8;border:2px dashed #f59e0b;border-radius:12px;margin-bottom:24px;">
            <tr><td style="padding:24px;text-align:center;">
              <p style="color:#92400e;font-size:13px;font-weight:600;margin:0 0 8px;text-transform:uppercase;letter-spacing:1px;">Seu cupom</p>
              <p style="font-family:monospace;font-size:28px;font-weight:700;color:#d97706;margin:0 0 8px;letter-spacing:4px;">{codigo_cupom}</p>
              <p style="color:#18181b;font-size:18px;font-weight:600;margin:0 0 4px;">{desconto} de desconto</p>
              <p style="color:#dc2626;font-size:14px;font-weight:600;margin:0;">Válido até {expira}</p>
            </td></tr>
          </table>

          <p style="color:#52525b;font-size:14px;line-height:1.6;margin:0;text-align:center;">
            Faça seu pedido agora e aproveite o desconto!
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#fafafa;padding:20px 40px;text-align:center;border-top:1px solid #e4e4e7;">
          <p style="color:#a1a1aa;font-size:12px;margin:0;">
            Derekh Food — Sistema de Delivery Inteligente<br>
            Este email foi enviado automaticamente.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return assunto, html

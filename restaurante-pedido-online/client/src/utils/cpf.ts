/**
 * Utilitário de validação e formatação de CPF
 */

/** Valida CPF usando algoritmo oficial (2 dígitos verificadores) */
export function validarCPF(cpf: string): boolean {
  const digits = cpf.replace(/\D/g, "");
  if (digits.length !== 11) return false;

  // Rejeitar CPFs com todos os dígitos iguais (000.000.000-00, 111.111.111-11, etc.)
  if (/^(\d)\1{10}$/.test(digits)) return false;

  // Validar primeiro dígito verificador
  let soma = 0;
  for (let i = 0; i < 9; i++) soma += Number(digits[i]) * (10 - i);
  let resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== Number(digits[9])) return false;

  // Validar segundo dígito verificador
  soma = 0;
  for (let i = 0; i < 10; i++) soma += Number(digits[i]) * (11 - i);
  resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== Number(digits[10])) return false;

  return true;
}

/** Formata CPF: 12345678901 → 123.456.789-01 */
export function formatarCPF(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

/** Remove formatação: 123.456.789-01 → 12345678901 */
export function limparCPF(cpf: string): string {
  return cpf.replace(/\D/g, "");
}

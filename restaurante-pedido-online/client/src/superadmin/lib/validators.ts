// superadmin/lib/validators.ts
// Máscaras e validações para formulários brasileiros (CPF, CNPJ, telefone, CEP)

export const DDDS_VALIDOS = new Set<number>([
  11, 12, 13, 14, 15, 16, 17, 18, 19,  // SP
  21, 22, 24,                            // RJ
  27, 28,                                // ES
  31, 32, 33, 34, 35, 37, 38,           // MG
  41, 42, 43, 44, 45, 46,               // PR
  47, 48, 49,                            // SC
  51, 53, 54, 55,                        // RS
  61,                                    // DF
  62, 64,                                // GO
  63,                                    // TO
  65, 66,                                // MT
  67,                                    // MS
  68,                                    // AC
  69,                                    // RO
  71, 73, 74, 75, 77,                   // BA
  79,                                    // SE
  81, 82, 83, 84, 85, 86, 87, 88, 89,  // PE/AL/PB/RN/CE/PI
  91, 92, 93, 94, 95, 96, 97, 98, 99,  // PA/AM/AP/RR/MA
]);

/** Formata telefone: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX */
export function formatarTelefone(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits.length ? `(${digits}` : "";
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10)
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

/** Formata CPF (XXX.XXX.XXX-XX) ou CNPJ (XX.XXX.XXX/XXXX-XX) */
export function formatarCpfCnpj(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 14);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  if (digits.length <= 9)
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  if (digits.length <= 11)
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
  // CNPJ
  if (digits.length <= 12)
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

/** Formata CEP: XXXXX-XXX */
export function formatarCep(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

/** Valida CPF pelo módulo 11 */
export function validarCpf(cpf: string): boolean {
  const digits = cpf.replace(/\D/g, "");
  if (digits.length !== 11) return false;
  // Rejeita todos iguais
  if (new Set(digits.split("")).size === 1) return false;

  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(digits[i]) * (10 - i);
  let resto = soma % 11;
  const d1 = resto < 2 ? 0 : 11 - resto;
  if (parseInt(digits[9]) !== d1) return false;

  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(digits[i]) * (11 - i);
  resto = soma % 11;
  const d2 = resto < 2 ? 0 : 11 - resto;
  return parseInt(digits[10]) === d2;
}

/** Valida CNPJ pelo módulo 11 */
export function validarCnpj(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, "");
  if (digits.length !== 14) return false;
  if (new Set(digits.split("")).size === 1) return false;

  const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  let soma = 0;
  for (let i = 0; i < 12; i++) soma += parseInt(digits[i]) * pesos1[i];
  let resto = soma % 11;
  const d1 = resto < 2 ? 0 : 11 - resto;
  if (parseInt(digits[12]) !== d1) return false;

  const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  soma = 0;
  for (let i = 0; i < 13; i++) soma += parseInt(digits[i]) * pesos2[i];
  resto = soma % 11;
  const d2 = resto < 2 ? 0 : 11 - resto;
  return parseInt(digits[13]) === d2;
}

/** Valida DDD brasileiro */
export function validarDDD(ddd: string): boolean {
  const num = parseInt(ddd, 10);
  if (isNaN(num)) return false;
  return DDDS_VALIDOS.has(num);
}

/** Valida telefone completo (DDD + número) */
export function validarTelefone(telefone: string): { valido: boolean; erro?: string } {
  const digits = telefone.replace(/\D/g, "");
  if (digits.length < 10 || digits.length > 11)
    return { valido: false, erro: "Telefone deve ter 10 ou 11 dígitos" };
  const ddd = parseInt(digits.slice(0, 2), 10);
  if (!DDDS_VALIDOS.has(ddd))
    return { valido: false, erro: `DDD ${String(ddd).padStart(2, "0")} inválido` };
  const numero = digits.slice(2);
  if (digits.length === 11 && numero[0] !== "9")
    return { valido: false, erro: "Celular deve começar com 9 após o DDD" };
  if (digits.length === 10 && !"2345".includes(numero[0]))
    return { valido: false, erro: "Fixo deve começar com 2-5 após o DDD" };
  return { valido: true };
}

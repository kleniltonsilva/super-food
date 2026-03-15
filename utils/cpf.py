"""Validação de CPF — algoritmo oficial com 2 dígitos verificadores."""


def validar_cpf(cpf: str) -> bool:
    """Valida CPF (aceita apenas dígitos, 11 chars)."""
    digits = ''.join(filter(str.isdigit, cpf))
    if len(digits) != 11:
        return False

    # Rejeitar CPFs com todos os dígitos iguais
    if len(set(digits)) == 1:
        return False

    # Primeiro dígito verificador
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(digits[9]):
        return False

    # Segundo dígito verificador
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(digits[10]):
        return False

    return True

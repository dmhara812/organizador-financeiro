from __future__ import annotations

import re

_HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def normalize_required_currency_code(value: str) -> str:
    """Normaliza códigos de moeda usados nos contratos da API.

    A aplicação usa códigos de três letras, como BRL e USD. Validar isso no
    schema evita que rotas e services recebam variações como espaços ou letras
    minúsculas.
    """

    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("A moeda deve ter exatamente 3 letras, como BRL ou USD.")
    return normalized


def normalize_optional_currency_code(value: str | None) -> str | None:
    """Aplica a mesma regra de moeda para campos opcionais."""

    if value is None:
        return None
    return normalize_required_currency_code(value)


def normalize_symbol(value: str) -> str:
    """Normaliza ticker/símbolo de ativo para reduzir duplicidade lógica."""

    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("O símbolo do ativo não pode ficar vazio.")
    return normalized


def normalize_optional_symbol(value: str | None) -> str | None:
    """Normaliza símbolo quando usado em filtros opcionais."""

    if value is None:
        return None
    return normalize_symbol(value)


def normalize_optional_upper(value: str | None) -> str | None:
    """Normaliza campos opcionais curtos que seguem convenção em caixa alta."""

    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def validate_optional_country_code(value: str | None) -> str | None:
    """Valida país no formato de duas letras, como BR ou US."""

    normalized = normalize_optional_upper(value)
    if normalized is None:
        return None
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("O país deve ter exatamente 2 letras, como BR ou US.")
    return normalized


def validate_optional_isin(value: str | None) -> str | None:
    """Valida ISIN quando informado.

    ISIN é opcional na v1, mas validar o formato quando enviado prepara o campo
    para integrações futuras e reduz sujeira cadastral.
    """

    normalized = normalize_optional_upper(value)
    if normalized is None:
        return None
    if not _ISIN_PATTERN.fullmatch(normalized):
        raise ValueError("O ISIN deve ter 12 caracteres no formato internacional.")
    return normalized


def validate_optional_hex_color(value: str | None) -> str | None:
    """Valida cor hexadecimal usada por categorias em gráficos futuros."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not _HEX_COLOR_PATTERN.fullmatch(normalized):
        raise ValueError("A cor deve estar em formato hexadecimal, como #0F766E.")
    return normalized.upper()

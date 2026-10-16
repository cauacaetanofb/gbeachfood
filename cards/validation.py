"""Validação compartilhada das entradas financeiras."""
import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from django.core.exceptions import ValidationError
from django.http import JsonResponse

MAX_AMOUNT = Decimal('99999999.99')
CENT = Decimal('0.01')


class InvalidInput(ValueError):
    pass


def money(value, minimum=CENT):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < minimum or amount > MAX_AMOUNT:
            raise InvalidInput('Valor fora do intervalo permitido.')
        rounded = amount.quantize(CENT)
        if rounded != amount:
            raise InvalidInput('Use no máximo duas casas decimais.')
        return rounded
    except (InvalidOperation, ValueError, TypeError) as error:
        raise InvalidInput('Valor inválido. Informe um valor positivo com até duas casas decimais.') from error


def positive_id(value):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise InvalidInput('Identificador inválido.')
    result = int(value)
    if not 0 < result <= 9223372036854775807:
        raise InvalidInput('Identificador inválido.')
    return result


def json_api(view):
    """Erros de entrada viram JSON; exceções de escrita continuam causando rollback."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            data = json.loads(request.body, parse_float=Decimal)
            if not isinstance(data, dict):
                raise InvalidInput('O corpo deve ser um objeto JSON.')
            request.json_data = data
            return view(request, *args, **kwargs)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except (InvalidInput, ValidationError) as error:
            message = str(error) if isinstance(error, InvalidInput) else 'Dados inválidos.'
            return JsonResponse({'error': message}, status=400)
    return wrapped

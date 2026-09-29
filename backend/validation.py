"""请求体校验辅助：非法输入统一抛 ValidationError，由应用级错误处理器转为 400。"""
from flask import request


class ValidationError(ValueError):
    """请求 body 缺失、不是合法 JSON、缺必填字段或字段类型 / 取值非法。"""


def get_json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('request body must be a valid JSON object')
    return data


def require_non_empty_string(data, field):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f'field "{field}" is required and must be a non-empty string'
        )
    return value


def _check_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f'field "{field}" must be a number')
    if value < 0:
        raise ValidationError(f'field "{field}" must not be negative')
    return value


def require_number(data, field):
    if field not in data or data[field] is None:
        raise ValidationError(f'field "{field}" is required')
    return _check_number(data[field], field)


def optional_number(data, field, default=None):
    value = data.get(field)
    if value is None:
        return default
    return _check_number(value, field)

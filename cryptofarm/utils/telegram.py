# cryptofarm/utils/telegram.py

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

def validate_telegram_data(init_data: str, bot_token: str) -> dict | None:
    """
    Проверяет целостность и подлинность initData, присланных из Telegram WebApp.
    Args:
        init_data: строка вида "foo=bar&baz=qux&user={...}&hash=...."
        bot_token: токен вашего бота из settings.TELEGRAM_BOT_TOKEN
    Returns:
        dict: распарсенные и проверенные данные (ключ 'user' уже десериализован как dict)
        None: если проверка не прошла
    """
    if not init_data:
        return None

    # Распарсим в словарь (parse_qsl разобьёт на пары key=val)
    data_dict = dict(parse_qsl(init_data, keep_blank_values=True))

    # 1) Забираем 'hash' и удаляем из data_dict, чтобы не включать при вычислении HMAC
    received_hash = data_dict.pop("hash", None)
    if not received_hash:
        return None

    # 2) Формируем data_check_string: сортируем все ключи (кроме hash) по алфавиту
    data_check_list = []
    for key, value in sorted(data_dict.items()):
        data_check_list.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_list)

    # 3) Вычисляем secret_key = SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

    # 4) Считаем hmac_sha256 от data_check_string
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    # 5) Сравниваем (с учётом тайминговой защиты)
    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    # 6) Проверяем, что auth_date не старше 24 часов
    try:
        auth_ts = int(data_dict.get("auth_date", "0"))
    except (ValueError, TypeError):
        return None

    if time.time() - auth_ts > 86400:
        return None

    # 7) Если в data_dict есть ключ 'user', это JSON-строка, распарсим её
    if "user" in data_dict:
        try:
            data_dict["user"] = json.loads(data_dict["user"])
        except (json.JSONDecodeError, TypeError):
            return None

    return data_dict


def extract_user_data(validated_data: dict) -> dict | None:
    """
    Берёт словарь validated_data, проверенный validate_telegram_data,
    и возвращает «чистый» словарь с полями пользователя:
      { 'telegram_id', 'username', 'first_name', 'last_name', 'photo_url' }
    Args:
      validated_data: результат validate_telegram_data (должен содержать ключ 'user')
    Returns:
      dict или None
    """
    if not validated_data or "user" not in validated_data:
        return None

    user_data = validated_data["user"]
    return {
        "telegram_id": user_data.get("id"),
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "photo_url": user_data.get("photo_url", "")
    }

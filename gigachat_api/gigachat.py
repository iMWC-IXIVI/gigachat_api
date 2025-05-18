import time
import httpx
import uuid

from pathlib import Path
from functools import wraps
from typing import Tuple


class GigaChat:
    """
    Асинхронный класс для обращения к API gigachat.

    Атрибуты:
        authorization: str - Ключ для авторизации в gigachat.
        scope : str - К какой версии API отправляется запрос.

    Методы:
        get_models() -> httpx:Response:
            Получить список моделей, который доступен данному ключу.

        send_message(type_model: str = 'GigaChat', message: str = '', prompt: str = '') -> httpx.Response:
            Ответ на вопрос от пользователя.
            Аргументы:
                type_model (str) - Название модели (по умолчанию GigaChat)
                message (str) - Сообщение от пользователя (по умолчанию пустая строка)
                prompt (str) - Инструкция для модели (по умолчанию пустая строка)
    """
    certificate_path = Path(__file__).resolve().parent/'certificate'/'russian_trusted_root_ca.cer'
    http_session = httpx.Client(verify=str(certificate_path))
    async_http_session = httpx.AsyncClient(verify=str(certificate_path))

    def __init__(self, authorization: str, scope: str) -> None:
        self.authorization = f'Basic {authorization}'
        self.scope = scope
        self.access_token, self.expire_token = self._get_access_token()

    def _get_access_token(self) -> Tuple[str, int]:
        url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': self.authorization
        }
        payload = {
            'scope': self.scope
        }
        response = self.http_session.post(url=url, headers=headers, data=payload)

        if response.status_code != 200:
            raise RuntimeError(f'Failed get a token - {response.status_code} - {response.text}')

        data = response.json()
        access_token = data.get('access_token')
        expire_token = data.get('expires_at')

        if not access_token or not expire_token:
            raise RuntimeError(f'Access token not found - {response.json()}')

        return access_token, expire_token

    @staticmethod
    def refresh_token(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            now = int(time.time())
            if now >= self.expire_token - 60:
                self.access_token, self.expire_token = self._get_access_token()
            return await func(self, *args, **kwargs)
        return wrapper

    @refresh_token
    async def get_models(self) -> httpx.Response:
        url = 'https://gigachat.devices.sberbank.ru/api/v1/models'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        return await self.async_http_session.get(url, headers=headers)

    @refresh_token
    async def send_message(self, type_model: str = 'GigaChat', message: str = '', prompt: str = '') -> httpx.Response:
        url = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        body = {
            'model': type_model,
            'messages': [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': message}
            ],
            'stream': False,
            'update_interval': 0
        }
        return await self.async_http_session.post(url=url, headers=headers, json=body)

    def close(self) -> None:
        self.http_session.close()

    async def aclose(self) -> None:
        await self.async_http_session.aclose()

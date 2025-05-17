import httpx
import uuid
import asyncio

from pathlib import Path


class GigaChat:
    certificate_path = Path(__file__).resolve().parent/'certificate'/'russian_trusted_root_ca.cer'
    http_session = httpx.Client(verify=str(certificate_path))
    async_http_session = httpx.AsyncClient(verify=str(certificate_path))

    def __init__(self, authorization, scope):
        self.authorization = f'Basic {authorization}'
        self.scope = scope
        self.access_token = self._get_access_token()

    def _get_access_token(self):
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

        access_token = response.json().get('access_token')

        if not access_token:
            raise RuntimeError(f'Access token not found - {response.json()}')

        return access_token

    async def get_models(self):
        url = 'https://gigachat.devices.sberbank.ru/api/v1/models'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        return await self.async_http_session.get(url, headers=headers)

#!/usr/bin/env python3
import json

from aiohttp import web
from aiohttp.web import FileResponse, Request, WebSocketResponse


class WSChat:
    def __init__(self, host='127.0.0.1', port=80):
        self.host = host
        self.port = port
        self.conns = {}

    @staticmethod
    async def main_page(request: Request) -> FileResponse:
        return FileResponse('./index.html')

    async def _broadcast(self, message: dict, ignore: set[str] = None) -> None:
        if ignore is None:
            ignore = set()
        await self._check_ws()
        for _id, ws in list(self.conns.items()):
            if _id in ignore:
                continue
            try:
                await ws.send_json(message)
            except ConnectionResetError:
                await self._leave_handler(_id)

    async def _websocket_chat(self, request: Request) -> None:
        ws = web.WebSocketResponse(autoping=False)
        if not ws.can_prepare(request):
            return
        await ws.prepare(request)

        async for msg in ws:
            data = msg.data
            if data == "ping":
                await ws.send_str("pong")
                await self._check_ws()
            elif json_data := json.loads(data):
                if json_data['mtype'] == "INIT":
                    await self._enter_handler(json_data, ws)
                elif json_data['mtype'] == "TEXT":
                    await self._message_handler(json_data)

    async def _enter_handler(self, data: dict, ws: WebSocketResponse) -> None:
        self.conns[data['id']] = ws
        await self._broadcast({'mtype': 'USER_ENTER', 'id': data['id']}, {data['id']})

    async def _message_handler(self, data: dict) -> None:
        if data['to'] is None:
            await self._broadcast({
                    'mtype': 'MSG',
                    'id': data['id'],
                    'text': data['text']
                }, {data['id']})
        else:
            await self.conns[data['to']].send_json({'mtype': 'DM', 'id': data['id'], 'text': data['text']})

    async def _check_ws(self) -> None:
        for _id, ws in list(self.conns.items()):
            if ws.closed:
                await self._leave_handler(_id)

    async def _leave_handler(self, _id: str) -> None:
        self.conns.pop(_id)
        await self._broadcast({'mtype': 'USER_LEAVE', 'id': _id})

    def run(self):
        app = web.Application()

        app.router.add_get('/', self.main_page)
        app.router.add_get('/chat', self._websocket_chat)

        web.run_app(app, host=self.host, port=self.port)


if __name__ == '__main__':
    WSChat('127.0.0.1', 80).run()

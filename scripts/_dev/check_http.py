"""Проверка HTTP изнутри контейнера: 127.0.0.1 и IP контейнера."""
import sys
import urllib.request

import socket

ip = socket.gethostbyname(socket.gethostname())
for host in ('127.0.0.1', ip):
    try:
        with urllib.request.urlopen(f'http://{host}:7777/health', timeout=5) as r:
            print(f'{host}: HTTP {r.status}, {len(r.read())} bytes')
    except Exception as e:
        print(f'{host}: FAIL {e!r}')

"""Админ-интерфейс (SPA на Jinja2 + JS)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))


@router.get('/admin', response_class=HTMLResponse)
def admin_page(request: Request):
    # Starlette >= 0.29: TemplateResponse(request, name[, context])
    return templates.TemplateResponse(request, 'admin.html')
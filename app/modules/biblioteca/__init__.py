# app/modules/biblioteca/__init__.py
from flask import Blueprint

biblioteca_bp = Blueprint('biblioteca', __name__, url_prefix='/biblioteca')

from app.modules.biblioteca import routes
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.edugest import EdugestModule
from app.database import db

# Definimos el Blueprint para el módulo de administración
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    """Muestra el panel principal y la matriz de configuración de módulos"""
    # Consultamos los módulos registrados en la base de datos SQLite
    modules = EdugestModule.query.all()
    return render_template('admin/dashboard.html', modules=modules)

@admin_bp.route('/toggle-module/<int:module_id>', methods=['POST'])
def toggle_module(module_id):
    """Acción rápida para habilitar o deshabilitar un módulo"""
    module = EdugestModule.query.get_or_404(module_id)
    module.IsEnabled = not module.IsEnabled
    db.session.commit()
    return redirect(url_for('admin.dashboard'))
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Ejecuta el servidor en modo depuración (Auto-reload al guardar cambios)
    app.run(debug=True, host='127.0.0.1', port=5000)
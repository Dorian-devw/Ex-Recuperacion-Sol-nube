import os
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
import database
import business

app = Flask(__name__, template_folder='templates', static_folder='static')

# Ruta para servir la UI frontend
@app.route('/')
def index():
    return render_template('index.html')

# --- ENDPOINTS API ---

# 1. Propietarios
@app.route('/api/owners', methods=['GET', 'POST'])
def manage_owners():
    if request.method == 'GET':
        return jsonify(business.get_owners())
    elif request.method == 'POST':
        try:
            data = request.json or {}
            owner_id = business.create_owner(data)
            return jsonify({"status": "success", "message": "Propietario registrado", "id": owner_id}), 201
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

# 2. Razas
@app.route('/api/breeds', methods=['GET'])
def get_breeds():
    especie = request.args.get('especie')
    return jsonify(business.get_breeds(especie))

# 3. Mascotas
@app.route('/api/pets', methods=['GET', 'POST'])
def manage_pets():
    if request.method == 'GET':
        return jsonify(business.get_pets())
    elif request.method == 'POST':
        try:
            data = request.json or {}
            pet_id = business.create_pet(data)
            return jsonify({"status": "success", "message": "Mascota registrada", "id": pet_id}), 201
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

# 4. Servicios
@app.route('/api/services', methods=['GET'])
def get_services():
    return jsonify(business.get_services())

# 5. Reservas
@app.route('/api/bookings', methods=['GET', 'POST'])
def manage_bookings():
    if request.method == 'GET':
        # Capturar filtros de la URL
        filters = {
            "mascota_id": request.args.get("mascota_id"),
            "propietario_id": request.args.get("propietario_id"),
            "servicio_id": request.args.get("servicio_id"),
            "fecha": request.args.get("fecha"),
            "estado": request.args.get("estado")
        }
        # Limpiar filtros vacíos
        filters = {k: v for k, v in filters.items() if v}
        return jsonify(business.get_bookings(filters))
    elif request.method == 'POST':
        try:
            data = request.json or {}
            booking_id = business.create_booking(data)
            return jsonify({"status": "success", "message": "Reserva registrada", "id": booking_id}), 201
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

# Inicialización de la base de datos al arrancar
def startup_db_init():
    max_retries = 15
    retry_interval = 3
    for i in range(max_retries):
        try:
            print(f"Intentando conectar a la base de datos (intento {i+1}/{max_retries})...")
            database.init_db()
            business.sync_breeds()
            print("Inicialización y sincronización de base de datos completa.")
            return True
        except Exception as e:
            print(f"No se pudo conectar a la base de datos: {e}")
            time.sleep(retry_interval)
    print("Fallo crítico: No se pudo establecer conexión con la base de datos tras varios intentos.")
    return False

# Ejecutar inicialización de BD
startup_db_init()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

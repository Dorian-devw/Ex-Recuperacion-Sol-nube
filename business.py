import os
import re
import requests
from datetime import datetime
import database

def sync_breeds():
    """
    Consumir la API de razas de perros (Dog API) al iniciar la aplicación,
    además de insertar algunas razas predefinidas de gatos para cumplir el requerimiento.
    """
    api_url = os.getenv("BREEDS_API_URL", "https://dog.ceo/api/breeds/list/all")
    print(f"Sincronizando razas desde: {api_url}")
    
    breeds_to_insert = []
    
    # Intentar consumir la Dog API
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                for breed in data.get("message", {}).keys():
                    # Formatear el nombre (ej. "german shepherd")
                    nombre_raza = breed.replace("-", " ").title()
                    breeds_to_insert.append((nombre_raza, "Perro"))
    except Exception as e:
        print(f"Error al consumir la Dog API: {e}. Se usarán razas de perro por defecto.")
        # Fallback de perros si la API falla
        breeds_to_insert.extend([
            ("Poodle", "Perro"),
            ("Golden Retriever", "Perro"),
            ("Pastor Alemán", "Perro"),
            ("Chihuahua", "Perro"),
            ("Labrador", "Perro")
        ])

    # Razas de gatos por defecto para complementar el requerimiento
    breeds_to_insert.extend([
        ("Persa", "Gato"),
        ("Siamés", "Gato"),
        ("Angora", "Gato"),
        ("Maine Coon", "Gato"),
        ("Bengala", "Gato"),
        ("Mestizo", "Gato"),
        ("Mestizo", "Perro") # Agregar mestizo para ambos
    ])

    # Guardar en base de datos
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            for nombre, especie in breeds_to_insert:
                cursor.execute(
                    "INSERT IGNORE INTO razas (nombre, especie) VALUES (%s, %s);",
                    (nombre, especie)
                )
        print("Sincronización de razas finalizada.")
    finally:
        conn.close()

# --- VALIDACIONES Y OPERACIONES ---

# 1. Propietarios
def get_owners():
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM propietarios ORDER BY apellidos, nombres;")
            return cursor.fetchall()
    finally:
        conn.close()

def create_owner(data):
    # Validar campos requeridos
    required = ['nombres', 'apellidos', 'documento_identidad', 'correo', 'telefono']
    for field in required:
        if not data.get(field) or not str(data[field]).strip():
            raise ValueError(f"El campo '{field}' es obligatorio.")

    correo = data['correo'].strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
        raise ValueError("El correo electrónico no es válido.")

    documento = data['documento_identidad'].strip()
    if not documento.isalnum():
        raise ValueError("El documento de identidad debe ser alfanumérico.")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            # Verificar si el documento ya está registrado
            cursor.execute("SELECT id FROM propietarios WHERE documento_identidad = %s;", (documento,))
            if cursor.fetchone():
                raise ValueError("Ya existe un propietario registrado con este documento de identidad.")
            
            cursor.execute(
                """INSERT INTO propietarios (nombres, apellidos, documento_identidad, correo, telefono)
                   VALUES (%s, %s, %s, %s, %s);""",
                (data['nombres'].strip(), data['apellidos'].strip(), documento, correo, data['telefono'].strip())
            )
            return cursor.lastrowid
    finally:
        conn.close()

# 2. Razas
def get_breeds(especie=None):
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            if especie:
                cursor.execute("SELECT * FROM razas WHERE especie = %s ORDER BY nombre;", (especie,))
            else:
                cursor.execute("SELECT * FROM razas ORDER BY especie, nombre;")
            return cursor.fetchall()
    finally:
        conn.close()

# 3. Mascotas
def get_pets():
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT m.*, r.nombre AS raza_nombre, 
                       CONCAT(p.nombres, ' ', p.apellidos) AS propietario_nombre
                FROM mascotas m
                JOIN razas r ON m.raza_id = r.id
                JOIN propietarios p ON m.propietario_id = p.id
                ORDER BY m.nombre;
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def create_pet(data):
    required = ['nombre', 'especie', 'raza_id', 'fecha_nacimiento', 'peso', 'sexo', 'propietario_id']
    for field in required:
        if data.get(field) is None or str(data[field]).strip() == "":
            raise ValueError(f"El campo '{field}' es obligatorio.")

    # Validar peso
    try:
        peso = float(data['peso'])
        if peso <= 0:
            raise ValueError("El peso debe ser mayor a cero.")
    except ValueError:
        raise ValueError("El peso debe ser un número válido.")

    # Validar fecha nacimiento no futura
    try:
        fecha_nac = datetime.strptime(str(data['fecha_nacimiento']), "%Y-%m-%d").date()
        if fecha_nac > datetime.now().date():
            raise ValueError("La fecha de nacimiento no puede ser una fecha futura.")
    except ValueError:
        raise ValueError("Formato de fecha de nacimiento inválido (debe ser AAAA-MM-DD).")

    # Validar sexo
    sexo = data['sexo'].strip().capitalize()
    if sexo not in ['Macho', 'Hembra']:
        raise ValueError("El sexo debe ser 'Macho' o 'Hembra'.")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            # Validar que propietario exista
            cursor.execute("SELECT id FROM propietarios WHERE id = %s;", (data['propietario_id'],))
            if not cursor.fetchone():
                raise ValueError("El propietario especificado no existe.")
            
            # Validar que raza exista
            cursor.execute("SELECT id FROM razas WHERE id = %s;", (data['raza_id'],))
            if not cursor.fetchone():
                raise ValueError("La raza especificada no existe.")

            cursor.execute(
                """INSERT INTO mascotas (nombre, especie, raza_id, fecha_nacimiento, peso, sexo, foto_url, propietario_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
                (data['nombre'].strip(), data['especie'].strip(), data['raza_id'], 
                 data['fecha_nacimiento'], peso, sexo, data.get('foto_url', '').strip(), data['propietario_id'])
            )
            return cursor.lastrowid
    finally:
        conn.close()

# 4. Servicios
def get_services():
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM servicios ORDER BY nombre;")
            return cursor.fetchall()
    finally:
        conn.close()

# 5. Reservas
def get_bookings(filters=None):
    query = """
        SELECT r.*, m.nombre AS mascota_nombre, m.especie AS mascota_especie,
               CONCAT(p.nombres, ' ', p.apellidos) AS propietario_nombre,
               s.nombre AS servicio_nombre
        FROM reservas r
        JOIN mascotas m ON r.mascota_id = m.id
        JOIN propietarios p ON m.propietario_id = p.id
        JOIN servicios s ON r.servicio_id = s.id
    """
    where_clauses = []
    params = []

    if filters:
        if filters.get("mascota_id"):
            where_clauses.append("r.mascota_id = %s")
            params.append(filters["mascota_id"])
        if filters.get("propietario_id"):
            where_clauses.append("m.propietario_id = %s")
            params.append(filters["propietario_id"])
        if filters.get("servicio_id"):
            where_clauses.append("r.servicio_id = %s")
            params.append(filters["servicio_id"])
        if filters.get("fecha"):
            where_clauses.append("r.fecha_atencion = %s")
            params.append(filters["fecha"])
        if filters.get("estado"):
            where_clauses.append("r.estado = %s")
            params.append(filters["estado"])

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY r.fecha_atencion DESC, r.hora_atencion DESC;"

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            # Formatear objetos de fecha y hora a strings
            for res in results:
                if 'fecha_atencion' in res:
                    res['fecha_atencion'] = str(res['fecha_atencion'])
                if 'hora_atencion' in res:
                    # En PyMySQL, las columnas TIME pueden devolverse como objetos timedelta
                    total_seconds = int(res['hora_atencion'].total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    res['hora_atencion'] = f"{hours:02d}:{minutes:02d}"
            return results
    finally:
        conn.close()

def create_booking(data):
    required = ['mascota_id', 'servicio_id', 'fecha_atencion', 'hora_atencion']
    for field in required:
        if not data.get(field) or not str(data[field]).strip():
            raise ValueError(f"El campo '{field}' es obligatorio.")

    # Validar fecha no pasada
    try:
        fecha_atencion = datetime.strptime(str(data['fecha_atencion']), "%Y-%m-%d").date()
        if fecha_atencion < datetime.now().date():
            raise ValueError("La fecha de atención no puede ser anterior a hoy.")
    except ValueError:
        raise ValueError("Formato de fecha inválido (debe ser AAAA-MM-DD).")

    # Validar hora
    try:
        datetime.strptime(str(data['hora_atencion']), "%H:%M")
    except ValueError:
        raise ValueError("Formato de hora inválido (debe ser HH:MM).")

    estado = data.get('estado', 'Pendiente').strip().capitalize()
    if estado not in ['Pendiente', 'Confirmada', 'Cancelada', 'Completada']:
        estado = 'Pendiente'

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            # Validar que mascota exista
            cursor.execute("SELECT id FROM mascotas WHERE id = %s;", (data['mascota_id'],))
            if not cursor.fetchone():
                raise ValueError("La mascota especificada no existe.")

            # Validar que servicio exista
            cursor.execute("SELECT id FROM servicios WHERE id = %s;", (data['servicio_id'],))
            if not cursor.fetchone():
                raise ValueError("El servicio especificado no existe.")

            cursor.execute(
                """INSERT INTO reservas (mascota_id, servicio_id, fecha_atencion, hora_atencion, observaciones, estado)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (data['mascota_id'], data['servicio_id'], data['fecha_atencion'], 
                 data['hora_atencion'], data.get('observaciones', '').strip(), estado)
            )
            return cursor.lastrowid
    finally:
        conn.close()

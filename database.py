import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "petcare_user"),
        password=os.getenv("DB_PASSWORD", "petcare_password"),
        database=os.getenv("DB_NAME", "petcare_db"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def init_db():
    # Intenta conectar al servidor sin base de datos seleccionada para crearla si no existe
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "petcare_user"),
        password=os.getenv("DB_PASSWORD", "petcare_password"),
        port=int(os.getenv("DB_PORT", 3306)),
        autocommit=True
    )
    db_name = os.getenv("DB_NAME", "petcare_db")
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    finally:
        conn.close()

    # Conecta a la base de datos específica para crear las tablas
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Tabla Propietarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS propietarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombres VARCHAR(100) NOT NULL,
                    apellidos VARCHAR(100) NOT NULL,
                    documento_identidad VARCHAR(20) NOT NULL UNIQUE,
                    correo VARCHAR(100) NOT NULL,
                    telefono VARCHAR(20) NOT NULL
                ) ENGINE=InnoDB;
            """)

            # 2. Tabla Razas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS razas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    especie VARCHAR(50) NOT NULL
                ) ENGINE=InnoDB;
            """)

            # 3. Tabla Mascotas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mascotas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    especie VARCHAR(50) NOT NULL,
                    raza_id INT NOT NULL,
                    fecha_nacimiento DATE NOT NULL,
                    peso DECIMAL(5,2) NOT NULL,
                    sexo VARCHAR(10) NOT NULL,
                    foto_url TEXT,
                    propietario_id INT NOT NULL,
                    FOREIGN KEY (raza_id) REFERENCES razas(id),
                    FOREIGN KEY (propietario_id) REFERENCES propietarios(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
            """)

            # 4. Tabla Servicios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servicios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    descripcion TEXT
                ) ENGINE=InnoDB;
            """)

            # 5. Tabla Reservas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reservas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mascota_id INT NOT NULL,
                    servicio_id INT NOT NULL,
                    fecha_atencion DATE NOT NULL,
                    hora_atencion TIME NOT NULL,
                    observaciones TEXT,
                    estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
                    FOREIGN KEY (mascota_id) REFERENCES mascotas(id) ON DELETE CASCADE,
                    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
                ) ENGINE=InnoDB;
            """)

            # Insertar servicios por defecto si la tabla está vacía
            cursor.execute("SELECT COUNT(*) as count FROM servicios;")
            if cursor.fetchone()['count'] == 0:
                servicios_defecto = [
                    ("Baño", "Servicio de baño y aseo general"),
                    ("Corte de pelo", "Corte estético y sanitario de pelaje"),
                    ("Consulta veterinaria", "Chequeo médico veterinario preventivo o por enfermedad"),
                    ("Vacunación", "Aplicación de vacunas y desparasitación"),
                    ("Paseo", "Paseos recreativos individuales o grupales"),
                    ("Hospedaje", "Alojamiento temporal por días con atención garantizada")
                ]
                cursor.executemany("INSERT INTO servicios (nombre, descripcion) VALUES (%s, %s);", servicios_defecto)

            print("Database initialized successfully with default tables and records.")
    finally:
        connection.close()

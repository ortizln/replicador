-- ============================================================
-- REPLICADOR PLATFORM - Esquema de Base de Datos
-- Motor: PostgreSQL 14+
-- ============================================================

-- Crear base de datos (ejecutar como superusuario)
-- CREATE DATABASE replicador_platform;
-- \c replicador_platform

-- ============================================================
-- 1. SERVIDORES
-- ============================================================
CREATE TABLE IF NOT EXISTS servidores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    host VARCHAR(100) NOT NULL,
    puerto INTEGER DEFAULT 22,
    usuario_ssh VARCHAR(100),
    clave_ssh TEXT,
    ruta_backups TEXT,
    tipo VARCHAR(50) DEFAULT 'ORIGEN',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

COMMENT ON TABLE servidores IS 'Servidores origen, destino, backup y recovery';
COMMENT ON COLUMN servidores.tipo IS 'ORIGEN | DESTINO | BACKUP | RECOVERY';

-- ============================================================
-- 2. BASES DE DATOS
-- ============================================================
CREATE TABLE IF NOT EXISTS bases_datos (
    id SERIAL PRIMARY KEY,
    id_servidor INTEGER NOT NULL REFERENCES servidores(id) ON DELETE CASCADE,
    motor VARCHAR(50) NOT NULL,
    nombre_bd VARCHAR(200) NOT NULL,
    host VARCHAR(100),
    puerto INTEGER,
    usuario_bd VARCHAR(100),
    password_bd TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE bases_datos IS 'Bases de datos registradas en cada servidor';
COMMENT ON COLUMN bases_datos.motor IS 'postgresql | mysql | mariadb | sqlserver';
COMMENT ON COLUMN bases_datos.password_bd IS 'Contraseña cifrada con Fernet';

-- ============================================================
-- 3. BACKUPS
-- ============================================================
CREATE TABLE IF NOT EXISTS backups (
    id SERIAL PRIMARY KEY,
    id_bd INTEGER NOT NULL REFERENCES bases_datos(id) ON DELETE CASCADE,
    fecha TIMESTAMP DEFAULT NOW(),
    tipo VARCHAR(50) DEFAULT 'COMPLETO',
    formato VARCHAR(20) DEFAULT '.dump',
    compresion VARCHAR(10),
    archivo TEXT NOT NULL,
    peso_bytes BIGINT,
    hash_sha256 VARCHAR(64),
    hash_verificado BOOLEAN DEFAULT FALSE,
    estado VARCHAR(50) DEFAULT 'PENDIENTE',
    destino_externo VARCHAR(100),
    transferido BOOLEAN DEFAULT FALSE,
    usuario VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE backups IS 'Archivos de respaldo generados';
COMMENT ON COLUMN backups.tipo IS 'COMPLETO | INCREMENTAL | DIFERENCIAL';
COMMENT ON COLUMN backups.formato IS '.dump | .sql | .backup | .tar';
COMMENT ON COLUMN backups.compresion IS 'gzip | zip | tar.gz';
COMMENT ON COLUMN backups.estado IS 'PENDIENTE | EXITOSO | FALLIDO | CORRUPTO';
COMMENT ON COLUMN backups.hash_sha256 IS 'SHA256 del archivo para verificar integridad';

CREATE INDEX idx_backups_fecha ON backups(fecha DESC);
CREATE INDEX idx_backups_id_bd ON backups(id_bd);
CREATE INDEX idx_backups_estado ON backups(estado);

-- ============================================================
-- 4. REPLICAS
-- ============================================================
CREATE TABLE IF NOT EXISTS replicas (
    id SERIAL PRIMARY KEY,
    origen_id INTEGER NOT NULL REFERENCES bases_datos(id),
    destino_id INTEGER NOT NULL REFERENCES bases_datos(id),
    tipo VARCHAR(50) DEFAULT 'COMPLETA',
    frecuencia VARCHAR(50) DEFAULT 'MANUAL',
    fecha TIMESTAMP DEFAULT NOW(),
    estado VARCHAR(50) DEFAULT 'PENDIENTE',
    filas_afectadas INTEGER DEFAULT 0,
    duracion_segundos REAL,
    detalle TEXT,
    usuario VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE replicas IS 'Historial de réplicas ejecutadas';
COMMENT ON COLUMN replicas.tipo IS 'COMPLETA | INCREMENTAL';
COMMENT ON COLUMN replicas.frecuencia IS 'MANUAL | DIARIO | SEMANAL';
COMMENT ON COLUMN replicas.estado IS 'PENDIENTE | EXITOSO | FALLIDO';

CREATE INDEX idx_replicas_fecha ON replicas(fecha DESC);
CREATE INDEX idx_replicas_estado ON replicas(estado);

-- ============================================================
-- 5. RESTAURACIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS restauraciones (
    id SERIAL PRIMARY KEY,
    backup_id INTEGER NOT NULL REFERENCES backups(id),
    servidor_id INTEGER NOT NULL REFERENCES servidores(id),
    base_datos_id INTEGER REFERENCES bases_datos(id),
    usuario VARCHAR(100),
    fecha TIMESTAMP DEFAULT NOW(),
    estado VARCHAR(50) DEFAULT 'PENDIENTE',
    detalle TEXT,
    duracion_segundos REAL
);

COMMENT ON TABLE restauraciones IS 'Historial de restauraciones de backups';
COMMENT ON COLUMN restauraciones.estado IS 'PENDIENTE | EXITOSO | FALLIDO';

CREATE INDEX idx_restauraciones_fecha ON restauraciones(fecha DESC);

-- ============================================================
-- 6. LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT NOW(),
    nivel VARCHAR(20) DEFAULT 'INFO',
    servicio VARCHAR(100),
    codigo VARCHAR(50),
    mensaje TEXT,
    detalle TEXT,
    id_servidor INTEGER REFERENCES servidores(id),
    id_backup INTEGER REFERENCES backups(id),
    id_replica INTEGER REFERENCES replicas(id),
    usuario VARCHAR(100),
    ip_origen VARCHAR(45)
);

COMMENT ON TABLE logs IS 'Registro de eventos del sistema';
COMMENT ON COLUMN logs.nivel IS 'INFO | WARN | ERROR | CRITICAL';

CREATE INDEX idx_logs_fecha ON logs(fecha DESC);
CREATE INDEX idx_logs_nivel ON logs(nivel);
CREATE INDEX idx_logs_servicio ON logs(servicio);

-- ============================================================
-- 7. AUDITORIA GENERAL
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria_general (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL,
    ip VARCHAR(45),
    accion VARCHAR(200) NOT NULL,
    entidad VARCHAR(100),
    entidad_id INTEGER,
    detalle TEXT,
    fecha TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE auditoria_general IS 'Auditoría de todas las acciones del sistema';
COMMENT ON COLUMN auditoria_general.accion IS 'Creó servidor | Ejecutó backup | Restauró respaldo | Eliminó backup | etc';

CREATE INDEX idx_auditoria_fecha ON auditoria_general(fecha DESC);
CREATE INDEX idx_auditoria_usuario ON auditoria_general(usuario);
CREATE INDEX idx_auditoria_accion ON auditoria_general(accion);

-- ============================================================
-- 8. FUNCIONES Y TRIGGERS
-- ============================================================

-- Actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_servidores_updated_at ON servidores;
CREATE TRIGGER trg_servidores_updated_at
    BEFORE UPDATE ON servidores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 9. CONFIGURACION
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(200) NOT NULL UNIQUE,
    valor TEXT
);

-- ============================================================
-- 10. HORARIOS (PROGRAMACIONES)
-- ============================================================
CREATE TABLE IF NOT EXISTS horarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    id_bd INTEGER REFERENCES bases_datos(id),
    id_origen INTEGER REFERENCES bases_datos(id),
    id_destino INTEGER REFERENCES bases_datos(id),
    formato VARCHAR(20) DEFAULT 'custom',
    compresion VARCHAR(10),
    cron_minuto VARCHAR(10) DEFAULT '0',
    cron_hora VARCHAR(10) DEFAULT '*',
    cron_dia VARCHAR(10) DEFAULT '*',
    cron_mes VARCHAR(10) DEFAULT '*',
    cron_semana VARCHAR(10) DEFAULT '*',
    activo BOOLEAN DEFAULT TRUE,
    ultima_ejecucion TIMESTAMP,
    ejecutando BOOLEAN DEFAULT FALSE,
    ultimo_resultado VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 11. USUARIOS DEL SISTEMA
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'OPERADOR',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE usuarios IS 'Usuarios del sistema con roles';
COMMENT ON COLUMN usuarios.rol IS 'ADMINISTRADOR | OPERADOR | AUDITOR';
COMMENT ON COLUMN usuarios.password IS 'SHA256 de la contraseña';

-- ============================================================
-- 12. DATOS INICIALES
-- ============================================================

-- Usuario administrador por defecto
-- password: admin123 (SHA256: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9)
INSERT INTO usuarios (username, password, rol, activo)
SELECT 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'ADMINISTRADOR', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin');

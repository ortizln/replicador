export interface Servidor {
  id?: number;
  nombre: string;
  host: string;
  puerto: number;
  usuario_ssh?: string;
  ruta_backups?: string;
  tipo: string;
  activo: boolean;
}

export interface BaseDatos {
  id?: number;
  id_servidor: number;
  motor: string;
  nombre_bd: string;
  host?: string;
  puerto?: number;
  usuario_bd?: string;
}

export interface Backup {
  id?: number;
  id_bd: number;
  fecha?: string;
  tipo: string;
  formato: string;
  compresion?: string;
  archivo: string;
  peso_bytes?: number;
  hash_sha256?: string;
  hash_verificado?: boolean;
  estado: string;
  transferido?: boolean;
  usuario?: string;
}

export interface Replica {
  id?: number;
  origen_id: number;
  destino_id: number;
  tipo: string;
  frecuencia: string;
  fecha?: string;
  estado: string;
  filas_afectadas?: number;
  duracion_segundos?: number;
  detalle?: string;
  usuario?: string;
}

export interface Restauracion {
  id?: number;
  backup_id: number;
  servidor_id: number;
  base_datos_id?: number;
  usuario?: string;
  fecha?: string;
  estado: string;
  detalle?: string;
  duracion_segundos?: number;
}

export interface LogEntry {
  id: number;
  fecha: string;
  nivel: string;
  servicio: string;
  codigo?: string;
  mensaje: string;
  detalle?: string;
  usuario?: string;
}

export interface DashboardResumen {
  backups_hoy: number;
  backups_exitosos_hoy: number;
  backups_fallidos_hoy: number;
  replicas_hoy: number;
  replicas_exitosas_hoy: number;
  replicas_fallidas_hoy: number;
  ultimo_backup: any;
  ultima_restauracion: any;
  espacio_consumido_bytes: number;
  errores_hoy: number;
  total_servidores: number;
  servidores_activos: number;
}

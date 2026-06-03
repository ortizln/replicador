import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Servidor, BaseDatos, Backup, Replica, Restauracion, LogEntry, DashboardResumen } from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  private params(obj?: any): HttpParams {
    let p = new HttpParams();
    if (obj) for (const k of Object.keys(obj)) if (obj[k] !== undefined && obj[k] !== null && obj[k] !== '') p = p.set(k, obj[k]);
    return p;
  }

  // Servidores
  getServidores(opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/servidores`, { params: this.params(opts) });
  }
  getServidor(id: number): Observable<Servidor> {
    return this.http.get<Servidor>(`${environment.apiUrl}/servidores/${id}`);
  }
  crearServidor(data: Servidor): Observable<any> {
    return this.http.post(`${environment.apiUrl}/servidores`, data);
  }
  actualizarServidor(id: number, data: Partial<Servidor>): Observable<any> {
    return this.http.put(`${environment.apiUrl}/servidores/${id}`, data);
  }
  eliminarServidor(id: number): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/servidores/${id}`);
  }
  testConexion(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/servidores/test-connection`, data);
  }

  // Bases de Datos
  getBasesDatos(idServidor?: number, opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    const p: any = { ...opts };
    if (idServidor) p.id_servidor = idServidor;
    return this.http.get(`${environment.apiUrl}/bases-datos`, { params: this.params(p) });
  }
  getBaseDatos(id: number): Observable<BaseDatos> {
    return this.http.get<BaseDatos>(`${environment.apiUrl}/bases-datos/${id}`);
  }
  crearBaseDatos(data: BaseDatos): Observable<any> {
    return this.http.post(`${environment.apiUrl}/bases-datos`, data);
  }
  actualizarBaseDatos(id: number, data: Partial<BaseDatos>): Observable<any> {
    return this.http.put(`${environment.apiUrl}/bases-datos/${id}`, data);
  }
  eliminarBaseDatos(id: number): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/bases-datos/${id}`);
  }
  testConexionBD(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/bases-datos/test-connection`, data);
  }

  // Backups
  getBackups(opts?: { id_bd?: number; page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/backups`, { params: this.params(opts) });
  }
  ejecutarBackup(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/backups`, data);
  }
  verificarBackup(id: number): Observable<any> {
    return this.http.post(`${environment.apiUrl}/backups/${id}/verificar`, {});
  }
  transferirBackup(id: number, data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/backups/${id}/transferir`, data);
  }
  eliminarBackup(id: number): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/backups/${id}`);
  }

  // Replicas
  getReplicas(opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/replicas`, { params: this.params(opts) });
  }
  ejecutarReplica(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/replicas`, data);
  }

  // Restauraciones
  getRestauraciones(opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/restauraciones`, { params: this.params(opts) });
  }
  ejecutarRestauracion(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/restauraciones`, data);
  }

  // Logs
  getLogs(params?: any): Observable<any> {
    return this.http.get(`${environment.apiUrl}/logs`, { params: this.params(params) });
  }

  // Dashboard
  getDashboard(): Observable<DashboardResumen> {
    return this.http.get<DashboardResumen>(`${environment.apiUrl}/dashboard/resumen`);
  }
  getBackupsPorDia(dias = 7): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/dashboard/backups-por-dia`, { params: this.params({ dias }) });
  }
  getErroresPorDia(dias = 7): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/dashboard/errores-por-dia`, { params: this.params({ dias }) });
  }

  // Config
  getTelegramConfig(): Observable<any> {
    return this.http.get(`${environment.apiUrl}/config/telegram`);
  }
  updateTelegramConfig(data: any): Observable<any> {
    return this.http.put(`${environment.apiUrl}/config/telegram`, data);
  }
  probarTelegram(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/config/telegram/probar`, data);
  }

  // Auto-transfer
  getAutoTransfer(): Observable<any> {
    return this.http.get(`${environment.apiUrl}/config/auto-transfer`);
  }
  updateAutoTransfer(data: any): Observable<any> {
    return this.http.put(`${environment.apiUrl}/config/auto-transfer`, data);
  }

  // Status
  getStatusActual(): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/status/actual`);
  }

  // Schedules
  getSchedules(opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/schedules`, { params: this.params(opts) });
  }
  crearSchedule(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/schedules`, data);
  }
  actualizarSchedule(id: number, data: any): Observable<any> {
    return this.http.put(`${environment.apiUrl}/schedules/${id}`, data);
  }
  eliminarSchedule(id: number): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/schedules/${id}`);
  }
  ejecutarScheduleAhora(id: number): Observable<any> {
    return this.http.post(`${environment.apiUrl}/schedules/${id}/ejecutar-ahora`, {});
  }

  // Usuarios
  getUsuarios(opts?: { page?: number; per_page?: number; sort_by?: string; sort_order?: string }): Observable<any> {
    return this.http.get(`${environment.apiUrl}/usuarios`, { params: this.params(opts) });
  }
  crearUsuario(data: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/usuarios`, data);
  }
  actualizarUsuario(id: number, data: any): Observable<any> {
    return this.http.put(`${environment.apiUrl}/usuarios/${id}`, data);
  }
  eliminarUsuario(id: number): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/usuarios/${id}`);
  }
}

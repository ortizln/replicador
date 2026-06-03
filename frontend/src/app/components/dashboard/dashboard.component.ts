import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { DashboardResumen } from '../../models';

@Component({
  selector: 'app-dashboard',
  template: `
    <div class="dashboard">
      <!-- KPI Cards -->
      <div class="row g-3 mb-4">
        <div class="col-xl-3 col-md-6">
          <div class="kpi-card kpi-primary">
            <div class="kpi-value">{{ data?.backups_exitosos_hoy || 0 }}</div>
            <div class="kpi-label">Backups Exitosos Hoy</div>
            <div class="kpi-icon">💾</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="kpi-card kpi-success">
            <div class="kpi-value">{{ data?.replicas_exitosas_hoy || 0 }}</div>
            <div class="kpi-label">Réplicas Exitosas Hoy</div>
            <div class="kpi-icon">🔄</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="kpi-card kpi-danger">
            <div class="kpi-value">{{ data?.errores_hoy || 0 }}</div>
            <div class="kpi-label">Errores Hoy</div>
            <div class="kpi-icon">⚠️</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="kpi-card kpi-info">
            <div class="kpi-value">{{ data?.total_servidores || 0 }}</div>
            <div class="kpi-label">Servidores Activos</div>
            <div class="kpi-icon">🖥️</div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <!-- Último Backup -->
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">📦 Último Backup</div>
            <div class="card-body">
              <ng-container *ngIf="data?.ultimo_backup?.fecha; else noBackup">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted small">Fecha</span>
                  <span class="fw-semibold">{{ data?.ultimo_backup?.fecha | date:'dd/MM/yyyy HH:mm' }}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted small">Estado</span>
                  <span class="badge" [class.badge-status-success]="data?.ultimo_backup?.estado === 'EXITOSO'"
                        [class.badge-status-error]="data?.ultimo_backup?.estado !== 'EXITOSO'">
                    {{ data?.ultimo_backup?.estado || 'N/A' }}
                  </span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                  <span class="text-muted small">Archivo</span>
                  <small class="text-truncate ms-2" style="max-width:180px">{{ data?.ultimo_backup?.archivo || 'N/A' }}</small>
                </div>
              </ng-container>
              <ng-template #noBackup>
                <div class="empty-state py-4">
                  <div class="empty-icon mb-2">📭</div>
                  <p class="mb-0 small">No hay backups registrados</p>
                </div>
              </ng-template>
            </div>
          </div>
        </div>

        <!-- Espacio Consumido -->
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">💾 Espacio Consumido</div>
            <div class="card-body d-flex flex-column align-items-center justify-content-center">
              <div class="display-4 fw-bold text-primary mb-1">{{ formatBytes(data?.espacio_consumido_bytes) }}</div>
              <span class="text-muted small">en backups almacenados</span>
              <div class="progress mt-3 w-100" style="height:8px">
                <div class="progress-bar bg-primary" role="progressbar" style="width:60%"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Última Restauración -->
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">⏪ Última Restauración</div>
            <div class="card-body">
              <ng-container *ngIf="data?.ultima_restauracion?.fecha; else noRestore">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted small">Fecha</span>
                  <span class="fw-semibold">{{ data?.ultima_restauracion?.fecha | date:'dd/MM/yyyy HH:mm' }}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted small">Estado</span>
                  <span class="badge" [class.badge-status-success]="data?.ultima_restauracion?.estado === 'EXITOSO'"
                        [class.badge-status-error]="data?.ultima_restauracion?.estado !== 'EXITOSO'">
                    {{ data?.ultima_restauracion?.estado || 'N/A' }}
                  </span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                  <span class="text-muted small">ID</span>
                  <span class="fw-semibold">#{{ data?.ultima_restauracion?.id || '-' }}</span>
                </div>
              </ng-container>
              <ng-template #noRestore>
                <div class="empty-state py-4">
                  <div class="empty-icon mb-2">📭</div>
                  <p class="mb-0 small">No hay restauraciones registradas</p>
                </div>
              </ng-template>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class DashboardComponent implements OnInit {
  data?: DashboardResumen;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getDashboard().subscribe(d => this.data = d);
  }

  formatBytes(bytes: number): string {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B','KB','MB','GB','TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}

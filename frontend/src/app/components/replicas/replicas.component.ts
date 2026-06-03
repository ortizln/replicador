import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { BaseDatos, Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-replicas',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar réplicas..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirFormEjecutar()">▶ Ejecutar Réplica</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando réplicas...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('id')"># <span *ngIf="sortBy==='id'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Origen</th>
              <th>Destino</th>
              <th class="sortable" (click)="toggleSort('tipo')">Tipo <span *ngIf="sortBy==='tipo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('frecuencia')">Frecuencia <span *ngIf="sortBy==='frecuencia'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('fecha')">Fecha <span *ngIf="sortBy==='fecha'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('filas_afectadas')">Filas <span *ngIf="sortBy==='filas_afectadas'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('estado')">Estado <span *ngIf="sortBy==='estado'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let r of items">
              <td class="text-muted">#{{ r.id }}</td>
              <td class="fw-semibold small">{{ nombreBd(r.origen_id) }}</td>
              <td class="small">{{ nombreBd(r.destino_id) }}</td>
              <td><span class="badge bg-light text-dark">{{ r.tipo }}</span></td>
              <td>{{ r.frecuencia }}</td>
              <td class="small">{{ r.fecha | date:'dd/MM/yyyy HH:mm' }}</td>
              <td>{{ r.filas_afectadas || '-' }}</td>
              <td>
                <span class="badge" [class.badge-status-success]="r.estado==='EXITOSO'"
                      [class.badge-status-error]="r.estado==='FALLIDO'"
                      [class.badge-status-warning]="r.estado==='PENDIENTE'">{{ r.estado }}</span>
              </td>
              <td class="text-end">
                <button class="btn-action btn-danger" (click)="eliminar(r.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">🔄</div>
        <h5>No hay réplicas</h5>
        <p class="small">Ejecuta tu primera réplica para comenzar</p>
        <button class="btn btn-primary btn-sm" (click)="abrirFormEjecutar()">▶ Ejecutar Réplica</button>
      </div>
    </div>

    <div class="modal fade" id="replicaModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">▶ Ejecutar Réplica</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Base Origen</label>
              <select class="form-select" [(ngModel)]="formReplica.origen_id">
                <option value="">Seleccionar...</option>
                <option *ngFor="let bd of basesDatos" [value]="bd.id">
                  <span class="fw-semibold">{{ bd.nombre_bd }}</span> <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Base Destino</label>
              <select class="form-select" [(ngModel)]="formReplica.destino_id">
                <option value="">Seleccionar...</option>
                <option *ngFor="let bd of basesDatos" [value]="bd.id">
                  <span class="fw-semibold">{{ bd.nombre_bd }}</span> <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Tipo</label>
              <select class="form-select" [(ngModel)]="formReplica.tipo">
                <option value="COMPLETA">Completa (pg_dump + pg_restore)</option>
                <option value="INCREMENTAL">Incremental</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Frecuencia</label>
              <select class="form-select" [(ngModel)]="formReplica.frecuencia">
                <option value="MANUAL">Manual</option>
                <option value="DIARIO">Diario</option>
                <option value="SEMANAL">Semanal</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="ejecutarReplica()" [disabled]="!formReplica.origen_id || !formReplica.destino_id || ejecutando">
              <span *ngIf="ejecutando" class="spinner-border spinner-border-sm me-1"></span>
              {{ ejecutando ? 'Ejecutando...' : '▶ Iniciar Réplica' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ReplicasComponent implements OnInit {
  items: any[] = [];
  filtro = '';
  basesDatos: BaseDatos[] = [];
  servidores: Servidor[] = [];
  formReplica: any = { origen_id: '', destino_id: '', tipo: 'COMPLETA', frecuencia: 'MANUAL' };
  sortBy = 'fecha';
  sortDir = 'desc';
  page = 1;
  total = 0;
  perPage = 20;
  loading = false;
  ejecutando = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.cargar();
    this.api.getBasesDatos(undefined, {}).subscribe(r => this.basesDatos = r.items);
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
  }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getReplicas(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  nombreBd(id: number) {
    const b = this.basesDatos.find(x => x.id === id);
    return b ? `${b.nombre_bd} (${b.motor})` : 'ID ' + id;
  }

  nombreServidor(id: number): string {
    const s = this.servidores.find(x => x.id === id);
    return s ? s.nombre : '?';
  }

  abrirFormEjecutar() {
    this.formReplica = { origen_id: '', destino_id: '', tipo: 'COMPLETA', frecuencia: 'MANUAL' };
    this.ejecutando = false;
    new (window as any).bootstrap.Modal(document.getElementById('replicaModal')).show();
  }

  ejecutarReplica() {
    this.ejecutando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('replicaModal'));
    this.api.ejecutarReplica(this.formReplica).subscribe({
      next: () => { modal.hide(); this.ejecutando = false; this.cargar(); },
      error: () => { this.ejecutando = false; }
    });
  }

  eliminar(id: number) { confirmDialog('¿Eliminar esta réplica?').then(r => { if (r) this.cargar(); }); }
}

import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-restauraciones',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar restauraciones..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirFormRestaurar()">⏪ Restaurar Backup</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando restauraciones...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('id')"># <span *ngIf="sortBy==='id'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Backup</th>
              <th>Servidor</th>
              <th class="sortable" (click)="toggleSort('usuario')">Usuario <span *ngIf="sortBy==='usuario'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('fecha')">Fecha <span *ngIf="sortBy==='fecha'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('duracion_segundos')">Duración <span *ngIf="sortBy==='duracion_segundos'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('estado')">Estado <span *ngIf="sortBy==='estado'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let r of items">
              <td class="text-muted">#{{ r.id }}</td>
              <td class="small">#{{ r.backup_id }}</td>
              <td class="small">{{ nombreServidor(r.servidor_id) }}</td>
              <td>{{ r.usuario || '-' }}</td>
              <td class="small">{{ r.fecha | date:'dd/MM/yyyy HH:mm' }}</td>
              <td>{{ r.duracion_segundos ? (r.duracion_segundos + 's') : '-' }}</td>
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
        <div class="empty-icon">⏪</div>
        <h5>No hay restauraciones</h5>
        <p class="small">Restaura un backup para comenzar</p>
        <button class="btn btn-primary btn-sm" (click)="abrirFormRestaurar()">⏪ Restaurar Backup</button>
      </div>
    </div>

    <div class="modal fade" id="restoreModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">⏪ Restaurar Backup</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Backup</label>
              <select class="form-select" [(ngModel)]="formRestore.backup_id">
                <option value="">Seleccionar...</option>
                <option *ngFor="let b of backups" [value]="b.id">#{{ b.id }} - {{ b.archivo }} ({{ b.fecha | date:'dd/MM/yyyy' }})</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Servidor Destino</label>
              <select class="form-select" [(ngModel)]="formRestore.servidor_id">
                <option value="">Seleccionar...</option>
                <option *ngFor="let s of servidores" [value]="s.id">{{ s.nombre }} ({{ s.host }})</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-warning text-white" (click)="ejecutarRestauracion()" [disabled]="!formRestore.backup_id || !formRestore.servidor_id || ejecutando">
              <span *ngIf="ejecutando" class="spinner-border spinner-border-sm me-1"></span>
              {{ ejecutando ? 'Restaurando...' : '⏪ Iniciar Restauración' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class RestauracionesComponent implements OnInit {
  items: any[] = [];
  filtro = '';
  backups: any[] = [];
  servidores: Servidor[] = [];
  formRestore: any = { backup_id: '', servidor_id: '' };
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
    this.api.getBackups({}).subscribe(r => this.backups = r.items);
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
  }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getRestauraciones(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  nombreServidor(id: number) {
    const s = this.servidores.find(x => x.id === id);
    return s ? `${s.nombre} (${s.host})` : 'ID ' + id;
  }

  abrirFormRestaurar() {
    this.formRestore = { backup_id: '', servidor_id: '' };
    this.ejecutando = false;
    new (window as any).bootstrap.Modal(document.getElementById('restoreModal')).show();
  }

  ejecutarRestauracion() {
    this.ejecutando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('restoreModal'));
    this.api.ejecutarRestauracion(this.formRestore).subscribe({
      next: () => { modal.hide(); this.ejecutando = false; this.cargar(); },
      error: () => { this.ejecutando = false; }
    });
  }

  eliminar(id: number) { confirmDialog('¿Eliminar este registro de restauración?').then(r => { if (r) this.cargar(); }); }
}

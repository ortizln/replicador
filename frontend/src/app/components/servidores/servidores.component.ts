import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-servidores',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar servidores..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" *ngIf="rol === 'ADMINISTRADOR'" (click)="abrirForm()">➕ Nuevo Servidor</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando servidores...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('id')"># <span *ngIf="sortBy==='id'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('nombre')">Nombre <span *ngIf="sortBy==='nombre'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('host')">Host <span *ngIf="sortBy==='host'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('puerto')">Puerto <span *ngIf="sortBy==='puerto'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('tipo')">Tipo <span *ngIf="sortBy==='tipo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('activo')">Estado <span *ngIf="sortBy==='activo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let s of items">
              <td class="text-muted">#{{ s.id }}</td>
              <td class="fw-semibold">{{ s.nombre }}</td>
              <td><code>{{ s.host }}</code></td>
              <td>{{ s.puerto }}</td>
              <td>
                <span class="badge" [class.badge-type-origen]="s.tipo==='ORIGEN'" [class.badge-type-destino]="s.tipo==='DESTINO'"
                      [class.badge-type-backup]="s.tipo==='BACKUP'" [class.badge-type-recovery]="s.tipo==='RECOVERY'">{{ s.tipo }}</span>
              </td>
              <td>
                <span class="badge" [class.badge-status-active]="s.activo" [class.badge-status-inactive]="!s.activo">{{ s.activo ? 'Activo' : 'Inactivo' }}</span>
              </td>
              <td class="text-end">
                <button class="btn-action me-1" (click)="editar(s)" title="Editar">✏️</button>
                <button class="btn-action btn-danger" (click)="eliminar(s.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">🖥️</div>
        <h5>No hay servidores</h5>
        <p class="small">Agrega tu primer servidor para comenzar</p>
        <button class="btn btn-primary btn-sm" *ngIf="rol === 'ADMINISTRADOR'" (click)="abrirForm()">+ Nuevo Servidor</button>
      </div>
    </div>

    <div class="modal fade" id="servidorModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editId ? 'Editar Servidor' : 'Nuevo Servidor' }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <form (ngSubmit)="guardar()">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">Nombre</label>
                  <input class="form-control" [(ngModel)]="form.nombre" name="nombre" required>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Host / IP</label>
                  <input class="form-control" [(ngModel)]="form.host" name="host" required>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Puerto SSH</label>
                  <input type="number" class="form-control" [(ngModel)]="form.puerto" name="puerto">
                </div>
                <div class="col-md-4">
                  <label class="form-label">Usuario SSH</label>
                  <input class="form-control" [(ngModel)]="form.usuario_ssh" name="usuario_ssh">
                </div>
                <div class="col-md-4">
                  <label class="form-label">Contraseña SSH</label>
                  <input type="password" class="form-control" [(ngModel)]="form.clave_ssh" name="clave_ssh" placeholder="Contraseña o ruta de clave SSH">
                </div>
                <div class="col-md-4">
                  <label class="form-label">Tipo</label>
                  <select class="form-select" [(ngModel)]="form.tipo" name="tipo">
                    <option value="ORIGEN">ORIGEN</option>
                    <option value="DESTINO">DESTINO</option>
                    <option value="BACKUP">BACKUP</option>
                    <option value="RECOVERY">RECOVERY</option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label">Ruta Backups</label>
                  <input class="form-control" [(ngModel)]="form.ruta_backups" name="ruta_backups">
                </div>
              </div>
            </form>
            <hr class="my-3">
            <div class="d-flex align-items-center gap-3">
              <button type="button" class="btn btn-outline-primary" (click)="probarConexion()" [disabled]="testLoading || !form.host">
                <span *ngIf="testLoading" class="spinner-border spinner-border-sm me-1"></span>
                🔌 Probar Conexión
              </button>
              <div *ngIf="testResultado" class="small" [class.text-success]="testResultado.ok" [class.text-danger]="!testResultado.ok">
                <strong>{{ testResultado.ok ? '✅ Conectado' : '❌ Error' }}</strong><br>
                {{ testResultado.mensaje || testResultado.error }}
                <span *ngIf="testResultado.info?.sistema" class="d-block text-muted mt-1">{{ testResultado.info.sistema }}</span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="guardar()" [disabled]="guardando">
              <span *ngIf="guardando" class="spinner-border spinner-border-sm me-1"></span>
              {{ editId ? 'Actualizando...' : 'Crear Servidor' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ServidoresComponent implements OnInit {
  items: Servidor[] = [];
  filtro = '';
  editId: number | null = null;
  form: any = { nombre: '', host: '', puerto: 22, usuario_ssh: '', ruta_backups: '', tipo: 'ORIGEN' };
  rol = localStorage.getItem('rol') || '';
  testLoading = false;
  testResultado: any = null;
  sortBy = 'id';
  sortDir = 'asc';
  page = 1;
  total = 0;
  perPage = 20;
  loading = false;
  guardando = false;

  constructor(private api: ApiService) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getServidores(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  abrirForm(s?: Servidor) {
    this.editId = s ? s.id! : null;
    this.form = s ? { ...s } : { nombre: '', host: '', puerto: 22, usuario_ssh: '', ruta_backups: '', tipo: 'ORIGEN' };
    this.testResultado = null;
    new (window as any).bootstrap.Modal(document.getElementById('servidorModal')).show();
  }

  editar(s: Servidor) { this.abrirForm(s); }

  probarConexion() {
    this.testLoading = true;
    this.testResultado = null;
    this.api.testConexion({ host: this.form.host, puerto: this.form.puerto, usuario_ssh: this.form.usuario_ssh, clave_ssh: this.form.clave_ssh || '' })
      .subscribe({ next: (res) => { this.testResultado = res; this.testLoading = false; }, error: (err) => { this.testResultado = err.error || { ok: false, error: 'Error de conexión' }; this.testLoading = false; } });
  }

  guardar() {
    this.guardando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('servidorModal'));
    const obs = this.editId ? this.api.actualizarServidor(this.editId, this.form) : this.api.crearServidor(this.form);
    obs.subscribe(() => { modal.hide(); this.guardando = false; this.cargar(); });
  }

  eliminar(id: number) {
    confirmDialog('¿Eliminar este servidor permanentemente?').then(r => { if (r) this.api.eliminarServidor(id).subscribe(() => this.cargar()); });
  }
}

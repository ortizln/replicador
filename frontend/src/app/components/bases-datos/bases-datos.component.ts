import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { BaseDatos, Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-bases-datos',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar bases de datos..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirForm()">➕ Nueva Base de Datos</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando bases de datos...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('id')"># <span *ngIf="sortBy==='id'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('nombre_bd')">Nombre <span *ngIf="sortBy==='nombre_bd'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Servidor</th>
              <th class="sortable" (click)="toggleSort('motor')">Motor <span *ngIf="sortBy==='motor'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('host')">Host <span *ngIf="sortBy==='host'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('puerto')">Puerto <span *ngIf="sortBy==='puerto'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Usuario</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let b of items">
              <td class="text-muted">#{{ b.id }}</td>
              <td class="fw-semibold">{{ b.nombre_bd }}</td>
              <td><span class="small text-muted">{{ nombreServidor(b.id_servidor) }}</span></td>
              <td><span class="badge bg-info">{{ b.motor }}</span></td>
              <td><code>{{ b.host }}</code></td>
              <td>{{ b.puerto }}</td>
              <td>{{ b.usuario_bd }}</td>
              <td class="text-end">
                <button class="btn-action me-1" (click)="editar(b)" title="Editar">✏️</button>
                <button class="btn-action btn-danger" (click)="eliminar(b.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">🗄️</div>
        <h5>No hay bases de datos</h5>
        <p class="small">Registra tu primera base de datos</p>
        <button class="btn btn-primary btn-sm" (click)="abrirForm()">+ Nueva Base de Datos</button>
      </div>
    </div>

    <div class="modal fade" id="bdModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editId ? 'Editar Base de Datos' : 'Nueva Base de Datos' }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Servidor</label>
              <select class="form-select" [(ngModel)]="form.id_servidor">
                <option value="">Seleccionar...</option>
                <option *ngFor="let s of servidores" [value]="s.id">{{ s.nombre }} ({{ s.host }})</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Nombre BD</label>
              <input class="form-control" [(ngModel)]="form.nombre_bd">
            </div>
            <div class="mb-3">
              <label class="form-label">Motor</label>
              <select class="form-select" [(ngModel)]="form.motor">
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="mariadb">MariaDB</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Host</label>
              <input class="form-control" [(ngModel)]="form.host">
            </div>
            <div class="row mb-3">
              <div class="col-6">
                <label class="form-label">Puerto</label>
                <input type="number" class="form-control" [(ngModel)]="form.puerto">
              </div>
              <div class="col-6">
                <label class="form-label">Usuario BD</label>
                <input class="form-control" [(ngModel)]="form.usuario_bd">
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">Contraseña BD</label>
              <input type="password" class="form-control" [(ngModel)]="form.password_bd">
            </div>
            <hr class="my-3">
            <div class="d-flex align-items-center gap-3">
              <button type="button" class="btn btn-outline-primary" (click)="probarConexion()"
                      [disabled]="testLoading || !form.host || !form.nombre_bd">
                <span *ngIf="testLoading" class="spinner-border spinner-border-sm me-1"></span>
                🗄️ Probar Conexión BD
              </button>
              <div *ngIf="testResultado" class="small" [class.text-success]="testResultado.ok" [class.text-danger]="!testResultado.ok">
                <strong>{{ testResultado.ok ? '✅ Conectado' : '❌ Error' }}</strong><br>
                {{ testResultado.mensaje || testResultado.error }}
                <span *ngIf="testResultado.info?.version" class="d-block text-muted mt-1">
                  {{ testResultado.info.version }}<br>
                  <span *ngIf="testResultado.info.tamano">Tamaño: {{ testResultado.info.tamano }}</span>
                </span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="guardar()" [disabled]="guardando">
              <span *ngIf="guardando" class="spinner-border spinner-border-sm me-1"></span>
              {{ editId ? 'Actualizando...' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class BasesDatosComponent implements OnInit {
  items: BaseDatos[] = [];
  filtro = '';
  servidores: Servidor[] = [];
  editId: number | null = null;
  form: any = { id_servidor: '', nombre_bd: '', motor: 'postgresql', host: '', puerto: 5432, usuario_bd: '', password_bd: '' };
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

  ngOnInit() {
    this.cargar();
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
  }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getBasesDatos(undefined, opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  nombreServidor(id: number) {
    const s = this.servidores.find(x => x.id === id);
    return s ? s.nombre + ' (' + s.host + ')' : '—';
  }

  abrirForm(bd?: BaseDatos) {
    this.editId = bd ? bd.id! : null;
    this.form = bd
      ? { id_servidor: bd.id_servidor, nombre_bd: bd.nombre_bd, motor: bd.motor, host: bd.host, puerto: bd.puerto, usuario_bd: bd.usuario_bd, password_bd: '' }
      : { id_servidor: '', nombre_bd: '', motor: 'postgresql', host: '', puerto: 5432, usuario_bd: '', password_bd: '' };
    this.testResultado = null;
    new (window as any).bootstrap.Modal(document.getElementById('bdModal')).show();
  }

  editar(bd: BaseDatos) { this.abrirForm(bd); }

  probarConexion() {
    this.testLoading = true;
    this.testResultado = null;
    this.api.testConexionBD({
      motor: this.form.motor, host: this.form.host, puerto: this.form.puerto,
      nombre_bd: this.form.nombre_bd, usuario_bd: this.form.usuario_bd, password_bd: this.form.password_bd,
    }).subscribe({
      next: (res) => { this.testResultado = res; this.testLoading = false; },
      error: (err) => { this.testResultado = err.error || { ok: false, error: 'Error de conexión' }; this.testLoading = false; }
    });
  }

  guardar() {
    this.guardando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('bdModal'));
    const obs = this.editId
      ? this.api.actualizarBaseDatos(this.editId, this.form)
      : this.api.crearBaseDatos(this.form);
    obs.subscribe(() => { modal.hide(); this.guardando = false; this.cargar(); });
  }

  eliminar(id: number) {
    confirmDialog('¿Eliminar esta base de datos?').then(r => { if (r) this.api.eliminarBaseDatos(id).subscribe(() => this.cargar()); });
  }
}

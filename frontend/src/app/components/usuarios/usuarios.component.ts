import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-usuarios',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirForm()">➕ Nuevo Usuario</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando usuarios...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('username')">Usuario <span *ngIf="sortBy==='username'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('rol')">Rol <span *ngIf="sortBy==='rol'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('activo')">Estado <span *ngIf="sortBy==='activo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Creado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let u of items">
              <td class="fw-semibold">{{ u.username }}</td>
              <td><span class="badge" [class.bg-warning]="u.rol==='ADMINISTRADOR'" [class.bg-info]="u.rol==='OPERADOR'" [class.bg-secondary]="u.rol==='AUDITOR'">{{ u.rol }}</span></td>
              <td>
                <span class="badge" [class.badge-status-active]="u.activo" [class.badge-status-inactive]="!u.activo">
                  {{ u.activo ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="small text-muted">{{ u.created_at ? (u.created_at | date:'dd/MM/yyyy') : '—' }}</td>
              <td class="text-end">
                <button class="btn-action me-1" (click)="editar(u)" title="Editar">✏️</button>
                <button class="btn-action btn-danger" (click)="eliminar(u.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">👥</div>
        <h5>No hay usuarios</h5>
        <p class="small">Crea un usuario para el sistema</p>
        <button class="btn btn-primary btn-sm" (click)="abrirForm()">➕ Nuevo Usuario</button>
      </div>
    </div>

    <div class="modal fade" id="usuarioModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nuevo' }} Usuario</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Usuario</label>
              <input class="form-control" [(ngModel)]="form.username">
            </div>
            <div class="mb-3">
              <label class="form-label">{{ editId ? 'Nueva contraseña (dejar vacío para mantener)' : 'Contraseña' }}</label>
              <input class="form-control" type="password" [(ngModel)]="form.password">
            </div>
            <div class="mb-3">
              <label class="form-label">Rol</label>
              <select class="form-select" [(ngModel)]="form.rol">
                <option value="ADMINISTRADOR">ADMINISTRADOR</option>
                <option value="OPERADOR">OPERADOR</option>
                <option value="AUDITOR">AUDITOR</option>
              </select>
            </div>
            <div class="mb-3 form-check">
              <input class="form-check-input" type="checkbox" id="activoCheck" [(ngModel)]="form.activo">
              <label class="form-check-label" for="activoCheck">Activo</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="guardar()" [disabled]="guardando">
              <span *ngIf="guardando" class="spinner-border spinner-border-sm me-1"></span>
              {{ editId ? 'Actualizar' : 'Crear' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class UsuariosComponent implements OnInit {
  items: any[] = [];
  filtro = '';
  editId: number | null = null;
  form: any = { username: '', password: '', rol: 'OPERADOR', activo: true };
  sortBy = 'username';
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
    this.api.getUsuarios(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  abrirForm(u?: any) {
    this.editId = u ? u.id : null;
    this.form = u ? { ...u, password: '' } : { username: '', password: '', rol: 'OPERADOR', activo: true };
    new (window as any).bootstrap.Modal(document.getElementById('usuarioModal')).show();
  }

  editar(u: any) { this.abrirForm(u); }

  guardar() {
    this.guardando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('usuarioModal'));
    const obs = this.editId ? this.api.actualizarUsuario(this.editId, this.form) : this.api.crearUsuario(this.form);
    obs.subscribe(() => { modal.hide(); this.guardando = false; this.cargar(); });
  }

  eliminar(id: number) {
    confirmDialog('¿Eliminar este usuario?').then(r => { if (r) this.api.eliminarUsuario(id).subscribe(() => this.cargar()); });
  }
}

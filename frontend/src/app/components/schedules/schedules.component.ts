import { Component, OnInit, OnDestroy } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { BaseDatos, Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-schedules',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirForm()">➕ Nueva Programación</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando programaciones...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('nombre')">Nombre <span *ngIf="sortBy==='nombre'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('tipo')">Tipo <span *ngIf="sortBy==='tipo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>BD / Detalle</th>
              <th>Programación (CRON)</th>
              <th class="sortable" (click)="toggleSort('activo')">Estado <span *ngIf="sortBy==='activo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Última ejec.</th>
              <th>Próxima ejec.</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let s of items">
              <td class="fw-semibold">{{ s.nombre }}</td>
              <td><span class="badge" [class.bg-info]="s.tipo==='BACKUP'" [class.bg-success]="s.tipo==='REPLICA'">{{ s.tipo }}</span></td>
              <td class="small">
                <span *ngIf="s.tipo==='BACKUP'">{{ nombreBd(s.id_bd) }}</span>
                <span *ngIf="s.tipo==='REPLICA'">{{ nombreBd(s.id_origen) }} &rarr; {{ nombreBd(s.id_destino) }}</span>
              </td>
              <td><code class="small">{{ s.cron_minuto }} {{ s.cron_hora }} {{ s.cron_dia }} {{ s.cron_mes }} {{ s.cron_semana }}</code></td>
              <td>
                <span class="badge" [class.badge-status-active]="s.activo" [class.badge-status-inactive]="!s.activo" style="cursor:pointer" (click)="toggleActivo(s)">
                  {{ s.activo ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="small text-muted">{{ s.ultima_ejecucion ? (s.ultima_ejecucion | date:'dd/MM/yyyy HH:mm') : '—' }}</td>
              <td class="small">
                <span *ngIf="s.ejecutando" class="text-warning">
                  <span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px"></span>
                  Ejecutando...
                </span>
                <span *ngIf="!s.ejecutando" class="text-primary">{{ s.proxima_ejecucion ? (s.proxima_ejecucion | date:'dd/MM/yyyy HH:mm') : '—' }}</span>
              </td>
              <td class="text-end">
                <button class="btn-action me-1" (click)="ejecutarAhora(s)" title="Ejecutar ahora" [disabled]="s.ejecutando">
                  <span *ngIf="s.ejecutando" class="spinner-border spinner-border-sm" style="width:12px;height:12px"></span>
                  <span *ngIf="!s.ejecutando">▶️</span>
                </button>
                <button class="btn-action me-1" (click)="editar(s)" title="Editar">✏️</button>
                <button class="btn-action btn-danger" (click)="eliminar(s.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">⏰</div>
        <h5>No hay programaciones</h5>
        <p class="small">Crea una programación para ejecutar backups o réplicas automáticamente</p>
        <button class="btn btn-primary btn-sm" (click)="abrirForm()">➕ Nueva Programación</button>
      </div>
    </div>

    <div class="modal fade" id="scheduleModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nueva' }} Programación</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Nombre</label>
              <input class="form-control" [(ngModel)]="form.nombre">
            </div>
            <div class="mb-3">
              <label class="form-label">Tipo</label>
              <select class="form-select" [(ngModel)]="form.tipo" (change)="form.id_bd=''; form.id_origen=''; form.id_destino=''">
                <option value="BACKUP">Backup</option>
                <option value="REPLICA">Réplica</option>
              </select>
            </div>
            <div class="mb-3" *ngIf="form.tipo==='BACKUP'">
              <label class="form-label">Base de Datos</label>
              <select class="form-select" [(ngModel)]="form.id_bd">
                <option value="">Seleccionar...</option>
                <option *ngFor="let bd of basesDatos" [value]="bd.id">
                  <span class="fw-semibold">{{ bd.nombre_bd }}</span> <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                </option>
              </select>
            </div>
            <div class="mb-3" *ngIf="form.tipo==='BACKUP'">
              <label class="form-label">Formato</label>
              <select class="form-select" [(ngModel)]="form.formato">
                <option value="custom">Custom (.dump)</option>
                <option value="plain">Plain SQL (.sql)</option>
                <option value="tar">Tar (.tar)</option>
              </select>
            </div>
            <div *ngIf="form.tipo==='REPLICA'">
              <div class="mb-3">
                <label class="form-label">Base Origen</label>
                <select class="form-select" [(ngModel)]="form.id_origen">
                  <option value="">Seleccionar...</option>
                  <option *ngFor="let bd of basesDatos" [value]="bd.id">
                    <span class="fw-semibold">{{ bd.nombre_bd }}</span> <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                  </option>
                </select>
              </div>
              <div class="mb-3">
                <label class="form-label">Base Destino</label>
                <select class="form-select" [(ngModel)]="form.id_destino">
                  <option value="">Seleccionar...</option>
                  <option *ngFor="let bd of basesDatos" [value]="bd.id">
                    <span class="fw-semibold">{{ bd.nombre_bd }}</span> <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                  </option>
                </select>
              </div>
            </div>
            <hr>
            <h6 class="small fw-semibold mb-2">⏰ Programación (CRON)</h6>
            <div class="row g-2">
              <div class="col">
                <label class="form-label small">Minuto</label>
                <input class="form-control form-control-sm" [(ngModel)]="form.cron_minuto" placeholder="0">
              </div>
              <div class="col">
                <label class="form-label small">Hora</label>
                <input class="form-control form-control-sm" [(ngModel)]="form.cron_hora" placeholder="*">
              </div>
              <div class="col">
                <label class="form-label small">Día</label>
                <input class="form-control form-control-sm" [(ngModel)]="form.cron_dia" placeholder="*">
              </div>
              <div class="col">
                <label class="form-label small">Mes</label>
                <input class="form-control form-control-sm" [(ngModel)]="form.cron_mes" placeholder="*">
              </div>
              <div class="col">
                <label class="form-label small">Semana</label>
                <input class="form-control form-control-sm" [(ngModel)]="form.cron_semana" placeholder="*">
              </div>
            </div>
            <div class="mt-2 small text-muted">
              Ej: <code>0 */2 * * *</code> = cada 2 horas &nbsp;|&nbsp; <code>30 23 * * *</code> = 11:30 PM diario
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

    <div class="modal fade" id="countdownModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
      <div class="modal-dialog modal-sm modal-dialog-centered">
        <div class="modal-content text-center">
          <div class="modal-body py-4">
            <div class="display-4 fw-bold text-primary mb-2">{{ countdown }}</div>
            <p class="mb-1">Ejecutando <strong>{{ countdownNombre }}</strong></p>
            <p class="small text-muted">en {{ countdown }} segundos...</p>
            <div class="progress mb-3" style="height:6px">
              <div class="progress-bar progress-bar-striped progress-bar-animated" [style.width.%]="(10 - countdown) * 10"></div>
            </div>
            <button class="btn btn-outline-danger btn-sm" (click)="cancelarCountdown()">Cancelar</button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class SchedulesComponent implements OnInit, OnDestroy {
  items: any[] = [];
  filtro = '';
  basesDatos: BaseDatos[] = [];
  servidores: Servidor[] = [];
  editId: number | null = null;
  form: any = { nombre: '', tipo: 'BACKUP', id_bd: '', id_origen: '', id_destino: '', formato: 'custom', compresion: '', cron_minuto: '0', cron_hora: '*', cron_dia: '*', cron_mes: '*', cron_semana: '*' };
  sortBy = 'nombre';
  sortDir = 'asc';
  page = 1;
  total = 0;
  perPage = 20;
  loading = false;
  guardando = false;
  countdown = 10;
  countdownNombre = '';
  private countdownTimer: any = null;
  private nuevoScheduleId: number | null = null;
  private pollTimer: any = null;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.cargar();
    this.api.getBasesDatos(undefined, {}).subscribe(r => this.basesDatos = r.items);
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
    this.pollTimer = setInterval(() => this.cargar(), 5000);
  }

  ngOnDestroy() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getSchedules(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  nombreBd(id: number) {
    const b = this.basesDatos.find(x => x.id === id);
    return b ? `${b.nombre_bd} (${b.motor})` : '—';
  }

  nombreServidor(id: number): string {
    const s = this.servidores.find(x => x.id === id);
    return s ? s.nombre : '?';
  }

  abrirForm(s?: any) {
    this.editId = s ? s.id : null;
    this.form = s ? { ...s } : { nombre: '', tipo: 'BACKUP', id_bd: '', id_origen: '', id_destino: '', formato: 'custom', compresion: '', cron_minuto: '0', cron_hora: '*', cron_dia: '*', cron_mes: '*', cron_semana: '*' };
    new (window as any).bootstrap.Modal(document.getElementById('scheduleModal')).show();
  }

  editar(s: any) { this.abrirForm(s); }

  toggleActivo(s: any) {
    this.api.actualizarSchedule(s.id, { activo: !s.activo }).subscribe(() => this.cargar());
  }

  guardar() {
    this.guardando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('scheduleModal'));
    const obs = this.editId ? this.api.actualizarSchedule(this.editId, this.form) : this.api.crearSchedule(this.form);
    obs.subscribe((res: any) => {
      modal.hide();
      this.guardando = false;
      this.cargar();
      if (!this.editId) {
        this.nuevoScheduleId = res.id;
        this.iniciarCountdown();
      }
    });
  }

  private iniciarCountdown() {
    this.countdown = 10;
    this.countdownNombre = this.form.nombre || 'Programación';
    const el = document.getElementById('countdownModal');
    if (!el) return;
    new (window as any).bootstrap.Modal(el).show();
    this.countdownTimer = setInterval(() => {
      this.countdown--;
      if (this.countdown <= 0) {
        this.ejecutarCountdown();
      }
    }, 1000);
  }

  private ejecutarCountdown() {
    this.detenerCountdown();
    if (this.nuevoScheduleId) {
      this.api.ejecutarScheduleAhora(this.nuevoScheduleId).subscribe();
    }
  }

  cancelarCountdown() {
    this.detenerCountdown();
    const el = document.getElementById('countdownModal');
    if (el) {
      const m = (window as any).bootstrap.Modal.getInstance(el);
      if (m) m.hide();
    }
  }

  private detenerCountdown() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    this.nuevoScheduleId = null;
  }

  ejecutarAhora(s: any) {
    this.api.ejecutarScheduleAhora(s.id).subscribe({
      next: () => { this.cargar(); },
      error: () => { s.ejecutando = false; }
    });
  }

  eliminar(id: number) {
    confirmDialog('¿Eliminar esta programación?').then(r => { if (r) this.api.eliminarSchedule(id).subscribe(() => this.cargar()); });
  }
}

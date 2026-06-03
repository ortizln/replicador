import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { BaseDatos, Servidor } from '../../models';
import { confirmDialog } from '../../utils/swal';

@Component({
  selector: 'app-backups',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar backups..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <button class="btn btn-primary" (click)="abrirFormEjecutar()">▶ Ejecutar Backup</button>
        <button class="btn btn-outline-primary" (click)="abrirFormSubir()">📤 Cargar Backup</button>
      </div>

      <div class="table-responsive">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando backups...</div>
        </div>
        <table class="table" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('id')"># <span *ngIf="sortBy==='id'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Origen</th>
              <th class="sortable" (click)="toggleSort('fecha')">Fecha/Hora <span *ngIf="sortBy==='fecha'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('tipo')">Tipo <span *ngIf="sortBy==='tipo'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('estado')">Estado <span *ngIf="sortBy==='estado'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('hash_sha256')">Hash SHA256 <span *ngIf="sortBy==='hash_sha256'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('peso_bytes')">Peso <span *ngIf="sortBy==='peso_bytes'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('usuario')">Usuario <span *ngIf="sortBy==='usuario'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let b of items">
              <td class="text-muted">{{ b.id }}</td>
              <td>
                <div class="fw-semibold small">{{ b.origen?.servidor || '—' }}</div>
                <div class="text-muted small">{{ b.origen?.nombre_bd }} <span class="badge bg-dark">{{ b.origen?.motor }}</span></div>
                <div class="text-muted small">{{ b.origen?.host }}:{{ b.origen?.puerto }}</div>
              </td>
              <td class="small">{{ b.fecha | date:'dd/MM/yyyy HH:mm:ss' }}</td>
              <td><span class="badge bg-light text-dark">{{ b.tipo }}</span></td>
              <td>
                <span class="badge" [class.badge-status-success]="b.estado==='EXITOSO'"
                      [class.badge-status-error]="b.estado==='FALLIDO'"
                      [class.badge-status-warning]="b.estado==='PENDIENTE'">{{ b.estado }}</span>
              </td>
              <td><code class="small" style="cursor:pointer" (click)="verDetalle(b)" title="Ver detalle">{{ (b.hash_sha256 || '') | slice:0:16 }}...</code></td>
              <td>{{ formatBytes(b.peso_bytes) }}</td>
              <td class="small text-muted">{{ b.usuario || '—' }}</td>
              <td class="text-end">
                <button class="btn-action me-1" (click)="verDetalle(b)" title="Ver bitácora">📋</button>
                <button class="btn-action me-1" (click)="verificar(b.id!)" title="Verificar integridad">🔐</button>
                <button class="btn-action me-1" (click)="transferir(b)" title="Transferir">📤</button>
                <button class="btn-action btn-danger" (click)="eliminar(b.id!)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">💾</div>
        <h5>Bítacora de respaldos vacía</h5>
        <p class="small">Ejecuta tu primer backup para comenzar</p>
        <button class="btn btn-primary btn-sm" (click)="abrirFormEjecutar()">▶ Ejecutar Backup</button>
      </div>
    </div>

    <div class="modal fade" id="detalleBackupModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">📋 Bítacora de Respaldo #{{ detalle?.id }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" *ngIf="detalle">
            <div class="row g-4">
              <div class="col-md-6">
                <div class="card bg-dark border-secondary h-100">
                  <div class="card-header border-secondary small fw-semibold">ORIGEN</div>
                  <div class="card-body small text-muted">
                    <div class="row mb-1"><div class="col-5">Servidor:</div><div class="col-7 fw-semibold text-light">{{ detalle.origen?.servidor || '—' }}</div></div>
                    <div class="row mb-1"><div class="col-5">BD:</div><div class="col-7 fw-semibold text-light">{{ detalle.origen?.nombre_bd }}</div></div>
                    <div class="row mb-1"><div class="col-5">Motor:</div><div class="col-7"><span class="badge bg-info">{{ detalle.origen?.motor }}</span></div></div>
                    <div class="row mb-1"><div class="col-5">Host:</div><div class="col-7">{{ detalle.origen?.host }}:{{ detalle.origen?.puerto }}</div></div>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="card bg-dark border-secondary h-100">
                  <div class="card-header border-secondary small fw-semibold">ARCHIVO</div>
                  <div class="card-body small text-muted">
                    <div class="row mb-1"><div class="col-4">Ruta:</div><div class="col-8 text-light" style="word-break:break-all">{{ detalle.archivo }}</div></div>
                    <div class="row mb-1"><div class="col-4">Formato:</div><div class="col-8">{{ detalle.formato }}</div></div>
                    <div class="row mb-1"><div class="col-4">Peso:</div><div class="col-8 fw-semibold text-light">{{ formatBytes(detalle.peso_bytes) }}</div></div>
                    <div class="row mb-1"><div class="col-4">Transferido:</div><div class="col-8">{{ detalle.transferido ? '✅ Sí' : '❌ No' }}</div></div>
                    <div class="row mb-1" *ngIf="detalle.destino_externo"><div class="col-4">Destino:</div><div class="col-8">{{ detalle.destino_externo }}</div></div>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="card bg-dark border-secondary h-100">
                  <div class="card-header border-secondary small fw-semibold">HASH & INTEGRIDAD</div>
                  <div class="card-body small text-muted">
                    <div class="row mb-1"><div class="col-12"><label class="fw-semibold text-light">SHA256:</label></div></div>
                    <div class="row mb-2"><div class="col-12"><code class="small" style="word-break:break-all">{{ detalle.hash_sha256 }}</code></div></div>
                    <div class="row mb-1"><div class="col-12">
                      <span class="badge" [class.badge-status-success]="detalle.hash_verificado" [class.badge-status-error]="!detalle.hash_verificado">
                        {{ detalle.hash_verificado ? '✅ Íntegro' : '⚠️ No verificado' }}
                      </span>
                    </div></div>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="card bg-dark border-secondary h-100">
                  <div class="card-header border-secondary small fw-semibold">METADATOS</div>
                  <div class="card-body small text-muted">
                    <div class="row mb-1"><div class="col-5">Fecha:</div><div class="col-7 text-light">{{ detalle.fecha | date:'dd/MM/yyyy HH:mm:ss' }}</div></div>
                    <div class="row mb-1"><div class="col-5">Tipo:</div><div class="col-7">{{ detalle.tipo }}</div></div>
                    <div class="row mb-1"><div class="col-5">Estado:</div><div class="col-7"><span class="badge" [class.badge-status-success]="detalle.estado==='EXITOSO'" [class.badge-status-error]="detalle.estado==='FALLIDO'">{{ detalle.estado }}</span></div></div>
                    <div class="row mb-1"><div class="col-5">Usuario:</div><div class="col-7 text-light">{{ detalle.usuario }}</div></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cerrar</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="backupModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">▶ Ejecutar Backup</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Base de Datos</label>
              <select class="form-select" [(ngModel)]="formBackup.id_bd">
                <option value="">Seleccionar...</option>
                <option *ngFor="let bd of basesDatos" [value]="bd.id">
                  <span class="fw-semibold">{{ bd.nombre_bd }}</span>
                  <small class="text-muted">({{ nombreServidor(bd.id_servidor!) }})</small>
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Formato</label>
              <select class="form-select" [(ngModel)]="formBackup.formato">
                <option value="custom">Custom (.dump)</option>
                <option value="plain">Plain SQL (.sql)</option>
                <option value="tar">Tar (.tar)</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Compresión</label>
              <select class="form-select" [(ngModel)]="formBackup.compresion">
                <option value="">Sin compresión</option>
                <option value="gzip">GZip</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="ejecutarBackup()" [disabled]="!formBackup.id_bd || ejecutando">
              <span *ngIf="ejecutando" class="spinner-border spinner-border-sm me-1"></span>
              {{ ejecutando ? 'Ejecutando...' : '▶ Iniciar Backup' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="transferModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">📤 Transferir Backup #{{ transferBackup?.id }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Servidor Destino</label>
              <select class="form-select" [(ngModel)]="transferForm.id_servidor">
                <option value="">Seleccionar...</option>
                <option *ngFor="let s of servidores" [value]="s.id">{{ s.nombre }} ({{ s.host }})</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Método</label>
              <select class="form-select" [(ngModel)]="transferForm.metodo">
                <option value="scp">SCP</option>
                <option value="sftp">SFTP</option>
                <option value="rsync">Rsync</option>
              </select>
            </div>
            <div class="small text-muted">
              Se transferirá <code>{{ transferBackup?.archivo }}</code>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" (click)="confirmarTransferencia()" [disabled]="!transferForm.id_servidor || transfiriendo">
              <span *ngIf="transfiriendo" class="spinner-border spinner-border-sm me-1"></span>
              {{ transfiriendo ? 'Transfiriendo...' : '📤 Transferir' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Modal -->
    <div class="modal fade" id="uploadModal" tabindex="-1" data-bs-backdrop="static">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">📤 Cargar Backup Manual</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Archivo de respaldo</label>
              <input class="form-control" type="file" (change)="onFileSelected($event)" accept=".dump,.sql,.backup,.tar,.gz">
            </div>
            <div class="mb-3">
              <label class="form-label">Servidor destino</label>
              <select class="form-select" [(ngModel)]="uploadForm.id_servidor">
                <option value="">Seleccionar...</option>
                <option *ngFor="let s of servidores" [value]="s.id">{{ s.nombre }} ({{ s.host }})</option>
              </select>
            </div>
            <div class="mb-3" *ngIf="uploadForm.id_servidor">
              <label class="form-label">Método de transferencia</label>
              <select class="form-select" [(ngModel)]="uploadForm.metodo">
                <option value="scp">SCP</option>
                <option value="sftp">SFTP</option>
                <option value="rsync">Rsync</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
            <button class="btn btn-primary" (click)="subirBackup()" [disabled]="subiendo || !uploadForm.id_servidor || !uploadFile">
              <span *ngIf="subiendo" class="spinner-border spinner-border-sm me-1"></span>
              {{ subiendo ? 'Subiendo...' : 'Cargar y Transferir' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class BackupsComponent implements OnInit {
  items: any[] = [];
  filtro = '';
  basesDatos: BaseDatos[] = [];
  servidores: Servidor[] = [];
  formBackup: any = { id_bd: '', formato: 'custom', compresion: '' };
  transferForm: any = { id_servidor: '', metodo: 'scp' };
  transferBackup: any = null;
  detalle: any = null;
  sortBy = 'fecha';
  sortDir = 'desc';
  page = 1;
  total = 0;
  perPage = 20;
  loading = false;
  ejecutando = false;
  transfiriendo = false;
  uploadForm: any = { id_servidor: '', metodo: 'scp' };
  uploadFile: File | null = null;
  subiendo = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.cargar();
    this.api.getBasesDatos(undefined, {}).subscribe(r => this.basesDatos = r.items);
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
  }

  cargar() {
    this.loading = true;
    const opts: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    this.api.getBackups(opts).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }

  abrirFormEjecutar() {
    this.formBackup = { id_bd: '', formato: 'custom', compresion: '' };
    this.ejecutando = false;
    new (window as any).bootstrap.Modal(document.getElementById('backupModal')).show();
  }

  ejecutarBackup() {
    this.ejecutando = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('backupModal'));
    this.api.ejecutarBackup(this.formBackup).subscribe({
      next: () => { modal.hide(); this.ejecutando = false; this.cargar(); },
      error: () => { this.ejecutando = false; }
    });
  }

  verDetalle(b: any) {
    this.detalle = b;
    new (window as any).bootstrap.Modal(document.getElementById('detalleBackupModal')).show();
  }

  verificar(id: number) {
    this.api.verificarBackup(id).subscribe((r: any) => {
      alert(r.resultado?.integro ? '✅ Backup íntegro' : '❌ Backup corrupto');
      this.cargar();
    });
  }

  transferir(b: any) {
    this.transferBackup = b;
    this.transferForm = { id_servidor: '', metodo: 'scp' };
    this.transfiriendo = false;
    new (window as any).bootstrap.Modal(document.getElementById('transferModal')).show();
  }

  confirmarTransferencia() {
    this.transfiriendo = true;
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('transferModal'));
    this.api.transferirBackup(this.transferBackup.id, this.transferForm).subscribe({
      next: () => { modal.hide(); this.transfiriendo = false; this.cargar(); },
      error: () => { this.transfiriendo = false; }
    });
  }

  abrirFormSubir() {
    this.uploadForm = { id_servidor: '', metodo: 'scp' };
    this.uploadFile = null;
    this.subiendo = false;
    new (window as any).bootstrap.Modal(document.getElementById('uploadModal')).show();
  }

  onFileSelected(event: any) {
    this.uploadFile = event.target.files?.[0] || null;
  }

  subirBackup() {
    if (!this.uploadFile || !this.uploadForm.id_servidor) return;
    const bd = this.basesDatos.find(x => x.id_servidor === this.uploadForm.id_servidor);
    if (!bd) { alert('El servidor seleccionado no tiene bases de datos asociadas'); return; }
    this.subiendo = true;
    const fd = new FormData();
    fd.append('file', this.uploadFile);
    fd.append('id_bd', String(bd.id));
    fd.append('transferir_a', String(this.uploadForm.id_servidor));
    fd.append('metodo', this.uploadForm.metodo);
    const modal = (window as any).bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
    this.api.subirBackup(fd).subscribe({
      next: () => { modal.hide(); this.subiendo = false; this.cargar(); },
      error: () => { this.subiendo = false; }
    });
  }

  eliminar(id: number) {
    confirmDialog('¿Eliminar este backup?').then(r => { if (r) this.api.eliminarBackup(id).subscribe(() => this.cargar()); });
  }

  nombreServidor(id: number) {
    const s = this.servidores.find(x => x.id === id);
    return s ? s.nombre + ' (' + s.host + ')' : '—';
  }

  formatBytes(bytes: number): string {
    if (!bytes) return '-';
    const k = 1024;
    const sizes = ['B','KB','MB','GB','TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}

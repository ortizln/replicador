import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-logs',
  template: `
    <div class="table-container">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" class="form-control" placeholder="Buscar en logs..." [(ngModel)]="filtro" (input)="cargar()">
        </div>
        <select class="form-select w-auto" [(ngModel)]="filtroNivel" (change)="cargar()">
          <option value="">Todos los niveles</option>
          <option value="INFO">INFO</option>
          <option value="WARN">WARN</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <select class="form-select w-auto" [(ngModel)]="filtroServicio" (change)="cargar()">
          <option value="">Todos los servicios</option>
          <option *ngFor="let s of servicios" [value]="s">{{ s }}</option>
        </select>
        <button class="btn btn-outline-secondary btn-sm" (click)="recargar()">🔄 Recargar</button>
      </div>

      <div class="table-responsive" style="max-height: calc(100vh - 320px)">
        <div *ngIf="loading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status"></div>
          <div class="small text-muted mt-1">Cargando logs...</div>
        </div>
        <table class="table table-sm" *ngIf="!loading && items.length > 0">
          <thead>
            <tr>
              <th class="sortable" (click)="toggleSort('fecha')">Fecha <span *ngIf="sortBy==='fecha'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('nivel')">Nivel <span *ngIf="sortBy==='nivel'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('servicio')">Servicio <span *ngIf="sortBy==='servicio'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th class="sortable" (click)="toggleSort('mensaje')">Mensaje <span *ngIf="sortBy==='mensaje'">{{ sortDir==='asc' ? '▲' : '▼' }}</span></th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let l of items" [class.table-danger]="l.nivel==='ERROR'||l.nivel==='CRITICAL'" [class.table-warning]="l.nivel==='WARN'">
              <td class="small text-nowrap">{{ l.fecha | date:'dd/MM/yyyy HH:mm:ss' }}</td>
              <td>
                <span class="badge" [class.bg-danger]="l.nivel==='ERROR'||l.nivel==='CRITICAL'"
                      [class.bg-warning]="l.nivel==='WARN'" [class.bg-info]="l.nivel==='INFO'">{{ l.nivel }}</span>
              </td>
              <td><code class="small">{{ l.servicio }}</code></td>
              <td class="small">{{ l.mensaje }}</td>
              <td class="small text-muted">{{ l.detalle || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <app-pagination *ngIf="!loading && total > perPage" [page]="page" [total]="total" [perPage]="perPage" (pageChange)="goPage($event)"></app-pagination>

      <div *ngIf="!loading && items.length === 0" class="empty-state">
        <div class="empty-icon">📋</div>
        <h5>No hay logs</h5>
        <p class="small">Los logs aparecerán cuando se ejecuten operaciones</p>
      </div>
    </div>
  `
})
export class LogsComponent implements OnInit {
  items: any[] = [];
  filtro = '';
  filtroNivel = '';
  filtroServicio = '';
  servicios: string[] = [];
  sortBy = 'fecha';
  sortDir = 'desc';
  page = 1;
  total = 0;
  perPage = 50;
  loading = false;

  constructor(private api: ApiService) {}

  ngOnInit() { this.recargar(); }

  recargar() {
    this.cargar();
    this.loading = true;
    this.api.getLogs({}).subscribe(r => {
      const logs = r.items || [];
      this.servicios = [...new Set<string>(logs.map((l: any) => l.servicio).filter(Boolean))];
      this.loading = false;
    });
  }

  cargar() {
    this.loading = true;
    const params: any = { page: this.page, per_page: this.perPage, sort_by: this.sortBy, sort_order: this.sortDir };
    if (this.filtro) params.mensaje = this.filtro;
    if (this.filtroNivel) params.nivel = this.filtroNivel;
    if (this.filtroServicio) params.servicio = this.filtroServicio;
    this.api.getLogs(params).subscribe(r => { this.items = r.items; this.total = r.total; this.loading = false; });
  }

  toggleSort(col: string) {
    if (this.sortBy === col) { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; }
    else { this.sortBy = col; this.sortDir = 'asc'; }
    this.page = 1; this.cargar();
  }

  goPage(p: number) { this.page = p; this.cargar(); }
}

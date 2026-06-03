import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  template: `
    <div class="app-layout" *ngIf="isLoggedIn()">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="brand-icon">🔄</div>
          <div class="brand-text">
            <div class="brand-title">Replicador</div>
            <div class="brand-subtitle">Platform</div>
          </div>
        </div>
        <nav class="sidebar-nav">
          <div class="nav-section">General</div>
          <a routerLink="/dashboard" routerLinkActive="active">
            <span class="nav-icon">📊</span> Dashboard
          </a>
          <a routerLink="/servidores" routerLinkActive="active">
            <span class="nav-icon">🖥️</span> Servidores
          </a>
          <a routerLink="/bases-datos" routerLinkActive="active">
            <span class="nav-icon">🗄️</span> Bases de Datos
          </a>
          <div class="nav-section">Operaciones</div>
          <a routerLink="/backups" routerLinkActive="active">
            <span class="nav-icon">💾</span> Backups
          </a>
          <a routerLink="/replicas" routerLinkActive="active">
            <span class="nav-icon">🔄</span> Réplicas
          </a>
          <a routerLink="/restauraciones" routerLinkActive="active">
            <span class="nav-icon">⏪</span> Restauraciones
          </a>
          <div class="nav-section">Monitoréo</div>
          <a routerLink="/logs" routerLinkActive="active">
            <span class="nav-icon">📋</span> Logs
          </a>
          <div class="nav-section">Sistema</div>
          <a routerLink="/schedules" routerLinkActive="active">
            <span class="nav-icon">⏰</span> Programaciones
          </a>
          <a routerLink="/usuarios" routerLinkActive="active" *ngIf="rol==='ADMINISTRADOR'">
            <span class="nav-icon">👥</span> Usuarios
          </a>
          <a routerLink="/config" routerLinkActive="active">
            <span class="nav-icon">⚙️</span> Configuración
          </a>
        </nav>
        <div class="sidebar-footer">
          <div class="user-avatar">{{ getInitial() }}</div>
          <div class="user-info">
            <div class="user-name">{{ username }}</div>
            <div class="user-rol">{{ rol }}</div>
          </div>
          <button class="btn-logout" (click)="logout()" title="Cerrar sesión">✕</button>
        </div>
      </aside>
      <div class="main-content">
        <header class="topbar">
          <h6 class="page-title mb-0">{{ currentTitle }}</h6>
          <div class="topbar-actions">
            <span *ngIf="tareasActivas.length > 0" class="status-indicator me-2" title="Operaciones en curso">
              <span class="spinner-border spinner-border-sm text-warning me-1"></span>
              <span class="small">{{ tareasActivas.length }} en ejecución</span>
            </span>
            <span class="badge bg-light text-dark px-3 py-2">{{ formatDate() }}</span>
          </div>
        </header>
        <div class="content-area">
          <div *ngIf="tareasActivas.length > 0" class="alert alert-warning d-flex align-items-center mb-0 rounded-0 border-0 small py-2" style="background:#664d03;color:#ffda6a;">
            <span class="spinner-border spinner-border-sm text-warning me-2"></span>
            <strong class="me-2">Operaciones en curso:</strong>
            <span *ngFor="let t of tareasActivas; let last=last">{{ t.descripcion }}<span *ngIf="!last">, </span></span>
          </div>
          <router-outlet></router-outlet>
        </div>
      </div>
    </div>
    <router-outlet *ngIf="!isLoggedIn()"></router-outlet>
  `
})
export class AppComponent implements OnInit, OnDestroy {
  rol = '';
  username = '';
  currentTitle = 'Dashboard';
  tareasActivas: any[] = [];
  private pollingTimer: any;

  private titles: Record<string, string> = {
    'dashboard': 'Dashboard',
    'servidores': 'Servidores',
    'bases-datos': 'Bases de Datos',
    'backups': 'Backups',
    'replicas': 'Réplicas',
    'restauraciones': 'Restauraciones',
    'logs': 'Logs & Auditoría',
    'config': 'Configuración',
    'schedules': 'Programaciones'
  };

  constructor(private router: Router, private api: ApiService) {}

  ngOnInit() {
    this.rol = localStorage.getItem('rol') || '';
    this.username = localStorage.getItem('username') || 'Admin';
    this.router.events.subscribe(() => {
      const segment = window.location.pathname.split('/')[1];
      this.currentTitle = this.titles[segment] || 'Dashboard';
    });
    this.iniciarPolling();
  }

  ngOnDestroy() { this.detenerPolling(); }

  iniciarPolling() {
    this.poll();
    this.pollingTimer = setInterval(() => this.poll(), 5000);
  }

  detenerPolling() { if (this.pollingTimer) clearInterval(this.pollingTimer); }

  poll() {
    if (!this.isLoggedIn()) return;
    this.api.getStatusActual().subscribe(r => this.tareasActivas = r);
  }

  getInitial(): string {
    return (this.username || 'A')[0].toUpperCase();
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('access_token');
  }

  logout() {
    localStorage.clear();
    this.router.navigate(['/login']);
  }

  formatDate(): string {
    return new Date().toLocaleDateString('es-ES', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  }
}

import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  template: `
    <div class="login-page">
      <div class="login-left">
        <div class="brand">
          <div class="brand-icon">⬡</div>
          <h1>Replicador Platform</h1>
          <p>Plataforma centralizada de replicación, respaldo y recuperación de bases de datos</p>
        </div>
      </div>
      <div class="login-right">
        <div class="login-header">
          <h2>Iniciar Sesión</h2>
          <p>Ingresa tus credenciales para acceder al sistema</p>
        </div>
        <form class="login-form" (ngSubmit)="onSubmit()" autocomplete="off">
          <div class="form-floating mb-3">
            <input type="text" class="form-control" id="username" placeholder="Usuario"
                   [(ngModel)]="username" name="username" required autocomplete="username">
            <label for="username">Usuario</label>
          </div>
          <div class="form-floating mb-3">
            <input type="password" class="form-control" id="password" placeholder="Contraseña"
                   [(ngModel)]="password" name="password" required autocomplete="current-password">
            <label for="password">Contraseña</label>
          </div>
          <div *ngIf="error" class="alert alert-danger py-2 small">{{ error }}</div>
          <button type="submit" class="btn-login" [disabled]="loading">
            <span *ngIf="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? 'Ingresando...' : 'Ingresar al Sistema' }}
          </button>
        </form>
        <p class="text-center text-muted small mt-4">© 2026 Replicador Platform v2.0</p>
      </div>
    </div>
  `
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';
  loading = false;

  constructor(private auth: AuthService, private router: Router) {}

  onSubmit() {
    if (!this.username || !this.password) return;
    this.loading = true;
    this.error = '';
    this.auth.login(this.username, this.password).subscribe({
      next: (res) => {
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('rol', res.rol);
        localStorage.setItem('username', this.username);
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.error = 'Credenciales inválidas. Verifica tu usuario y contraseña.';
        this.loading = false;
      }
    });
  }
}

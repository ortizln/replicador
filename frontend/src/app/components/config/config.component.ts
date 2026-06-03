import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { Servidor } from '../../models';

@Component({
  selector: 'app-config',
  template: `
    <div class="table-container p-4">
      <h5 class="mb-4 fw-bold">⚙️ Configuración</h5>

      <div class="card">
        <div class="card-body">
          <h6 class="card-title">🤖 Telegram</h6>
          <p class="small text-muted mb-3">Recibe notificaciones de backups y réplicas en tu Telegram.</p>

          <div class="mb-3">
            <label class="form-label">Bot Token</label>
            <input type="password" class="form-control" [(ngModel)]="formTelegram.TELEGRAM_BOT_TOKEN"
                   placeholder="123456:ABC-def_GHI...">
          </div>
          <div class="mb-3">
            <label class="form-label">Chat ID</label>
            <input class="form-control" [(ngModel)]="formTelegram.TELEGRAM_CHAT_ID"
                   placeholder="-123456789 o 123456789">
          </div>

          <div class="d-flex align-items-center gap-3">
            <button class="btn btn-primary" (click)="guardarTelegram()" [disabled]="loadingTelegram">
              <span *ngIf="loadingTelegram" class="spinner-border spinner-border-sm me-1"></span>
              Guardar Configuración
            </button>
            <button class="btn btn-outline-info" (click)="probar()" [disabled]="probando || !formTelegram.TELEGRAM_BOT_TOKEN || !formTelegram.TELEGRAM_CHAT_ID">
              <span *ngIf="probando" class="spinner-border spinner-border-sm me-1"></span>
              Enviar Prueba
            </button>
            <span *ngIf="mensajeTelegram" class="small" [class.text-success]="mensajeTelegramOk" [class.text-danger]="!mensajeTelegramOk">{{ mensajeTelegram }}</span>
          </div>
        </div>
      </div>

      <div class="card mt-3">
        <div class="card-body">
          <h6 class="card-title">📤 Auto-Transferencia</h6>
          <p class="small text-muted mb-3">Transfiere automáticamente los backups a uno o más servidores al finalizar.</p>

          <div class="mb-3 form-check form-switch">
            <input class="form-check-input" type="checkbox" id="autoTransferActivo" [(ngModel)]="formAuto.activo">
            <label class="form-check-label" for="autoTransferActivo">Activar auto-transferencia</label>
          </div>

          <div class="mb-3">
            <label class="form-label">Servidores destino</label>
            <div *ngFor="let s of servidores" class="form-check">
              <input class="form-check-input" type="checkbox" [id]="'srv'+s.id"
                     [checked]="formAuto.servidores.includes(s.id!)"
                     (change)="toggleServidor(s.id!)">
              <label class="form-check-label" [for]="'srv'+s.id">{{ s.nombre }} ({{ s.host }})</label>
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label">Método de transferencia</label>
            <select class="form-select" [(ngModel)]="formAuto.metodo">
              <option value="scp">SCP</option>
              <option value="sftp">SFTP</option>
              <option value="rsync">Rsync</option>
            </select>
          </div>

          <button class="btn btn-primary" (click)="guardarAuto()" [disabled]="loadingAuto">
            <span *ngIf="loadingAuto" class="spinner-border spinner-border-sm me-1"></span>
            Guardar Auto-Transferencia
          </button>
          <span *ngIf="mensajeAuto" class="small ms-2" [class.text-success]="mensajeAutoOk" [class.text-danger]="!mensajeAutoOk">{{ mensajeAuto }}</span>
        </div>
      </div>
    </div>
  `
})
export class ConfigComponent implements OnInit {
  formTelegram: any = { TELEGRAM_BOT_TOKEN: '', TELEGRAM_CHAT_ID: '' };
  formAuto: any = { activo: false, servidores: [], metodo: 'scp' };
  servidores: Servidor[] = [];
  loadingTelegram = false;
  probando = false;
  mensajeTelegram = '';
  mensajeTelegramOk = false;
  loadingAuto = false;
  mensajeAuto = '';
  mensajeAutoOk = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getTelegramConfig().subscribe(r => this.formTelegram = r);
    this.api.getServidores({}).subscribe(r => this.servidores = r.items);
    this.api.getAutoTransfer().subscribe(r => this.formAuto = r);
  }

  toggleServidor(id: number) {
    const idx = this.formAuto.servidores.indexOf(id);
    if (idx >= 0) this.formAuto.servidores.splice(idx, 1);
    else this.formAuto.servidores.push(id);
  }

  guardarTelegram() {
    this.loadingTelegram = true;
    this.mensajeTelegram = '';
    this.api.updateTelegramConfig(this.formTelegram).subscribe({
      next: () => { this.mensajeTelegram = '✅ Configuración guardada'; this.mensajeTelegramOk = true; this.loadingTelegram = false; },
      error: () => { this.mensajeTelegram = '❌ Error al guardar'; this.mensajeTelegramOk = false; this.loadingTelegram = false; }
    });
  }

  probar() {
    this.probando = true;
    this.mensajeTelegram = '';
    this.api.probarTelegram(this.formTelegram).subscribe({
      next: (r) => { this.mensajeTelegram = r.mensaje; this.mensajeTelegramOk = r.ok; this.probando = false; },
      error: (e) => { this.mensajeTelegram = e.error?.mensaje || '❌ Error al enviar prueba'; this.mensajeTelegramOk = false; this.probando = false; }
    });
  }

  guardarAuto() {
    this.loadingAuto = true;
    this.mensajeAuto = '';
    this.api.updateAutoTransfer(this.formAuto).subscribe({
      next: () => { this.mensajeAuto = '✅ Guardado'; this.mensajeAutoOk = true; this.loadingAuto = false; },
      error: () => { this.mensajeAuto = '❌ Error'; this.mensajeAutoOk = false; this.loadingAuto = false; }
    });
  }
}

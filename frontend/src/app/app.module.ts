import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RouterModule, Routes } from '@angular/router';

import { AppComponent } from './app.component';
import { LoginComponent } from './components/login/login.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { ServidoresComponent } from './components/servidores/servidores.component';
import { BasesDatosComponent } from './components/bases-datos/bases-datos.component';
import { BackupsComponent } from './components/backups/backups.component';
import { ReplicasComponent } from './components/replicas/replicas.component';
import { RestauracionesComponent } from './components/restauraciones/restauraciones.component';
import { LogsComponent } from './components/logs/logs.component';
import { ConfigComponent } from './components/config/config.component';
import { SchedulesComponent } from './components/schedules/schedules.component';
import { UsuariosComponent } from './components/usuarios/usuarios.component';
import { PaginationComponent } from './components/pagination/pagination.component';
import { AuthGuard } from './guards';
import { JwtInterceptor } from './guards/jwt.interceptor';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'servidores', component: ServidoresComponent, canActivate: [AuthGuard] },
  { path: 'bases-datos', component: BasesDatosComponent, canActivate: [AuthGuard] },
  { path: 'backups', component: BackupsComponent, canActivate: [AuthGuard] },
  { path: 'replicas', component: ReplicasComponent, canActivate: [AuthGuard] },
  { path: 'restauraciones', component: RestauracionesComponent, canActivate: [AuthGuard] },
  { path: 'logs', component: LogsComponent, canActivate: [AuthGuard] },
  { path: 'config', component: ConfigComponent, canActivate: [AuthGuard] },
  { path: 'schedules', component: SchedulesComponent, canActivate: [AuthGuard] },
  { path: 'usuarios', component: UsuariosComponent, canActivate: [AuthGuard] },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
];

@NgModule({
  declarations: [AppComponent, LoginComponent, DashboardComponent, ServidoresComponent, BasesDatosComponent, BackupsComponent, ReplicasComponent, RestauracionesComponent, LogsComponent, ConfigComponent, SchedulesComponent, UsuariosComponent, PaginationComponent],
  imports: [BrowserModule, FormsModule, HttpClientModule, RouterModule.forRoot(routes)],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}

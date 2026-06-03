import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-pagination',
  template: `
    <div class="pagination-wrapper" *ngIf="totalPages > 1">
      <nav>
        <ul class="pagination justify-content-center mb-0">
          <li class="page-item" [class.disabled]="page <= 1">
            <a class="page-link" (click)="go(page - 1)">«</a>
          </li>
          <li class="page-item" *ngFor="let p of pages" [class.active]="p === page">
            <a class="page-link" (click)="go(p)">{{ p }}</a>
          </li>
          <li class="page-item" [class.disabled]="page >= totalPages">
            <a class="page-link" (click)="go(page + 1)">»</a>
          </li>
        </ul>
      </nav>
      <div class="text-muted small text-center mt-1">{{ total }} registros — Pág {{ page }} de {{ totalPages }}</div>
    </div>
  `,
  styles: [`
    .pagination-wrapper { padding: 12px 0 4px; }
    .pagination { margin: 0; gap: 2px; }
    .page-item .page-link {
      background: var(--bs-dark); border: 1px solid var(--bs-border-color);
      color: var(--bs-body-color); cursor: pointer; padding: 4px 10px; font-size: 0.85rem;
    }
    .page-item.active .page-link { background: var(--bs-primary); border-color: var(--bs-primary); color: #fff; }
    .page-item.disabled .page-link { opacity: 0.4; cursor: default; }
  `]
})
export class PaginationComponent {
  @Input() page = 1;
  @Input() total = 0;
  @Input() perPage = 20;
  @Output() pageChange = new EventEmitter<number>();

  get totalPages() { return Math.ceil(this.total / this.perPage) || 1; }

  get pages(): number[] {
    const tp = this.totalPages;
    const current = this.page;
    if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1);
    const start = Math.max(2, current - 2);
    const end = Math.min(tp - 1, current + 2);
    const arr: number[] = [1];
    if (start > 2) arr.push(-1);
    for (let i = start; i <= end; i++) arr.push(i);
    if (end < tp - 1) arr.push(-1);
    if (tp > 1) arr.push(tp);
    return arr;
  }

  go(p: number) { if (p >= 1 && p <= this.totalPages) this.pageChange.emit(p); }
}

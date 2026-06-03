import Swal from 'sweetalert2';

export function confirmDialog(title: string): Promise<boolean> {
  return Swal.fire({
    title,
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#dc3545',
    reverseButtons: true,
  }).then(r => r.isConfirmed);
}

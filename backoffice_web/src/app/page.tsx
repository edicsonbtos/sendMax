import { redirect } from 'next/navigation';

export default function RootPage() {
    // Protocolo Sendmax 2.0: Root redirige a login por defecto
    redirect('/login');
}

import { redirect } from 'next/navigation';

export default function RootPage() {
    // Protocolo Sendmax 2.0: Root redirige al Dashboard 10x
    redirect('/admin');
}

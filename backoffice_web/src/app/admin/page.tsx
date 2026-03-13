'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/control-center');
  }, [router]);

  return (
    <div className="flex items-center justify-center h-screen bg-black">
      <div className="animate-pulse text-blue-500 font-black tracking-widest uppercase text-xs">
        Redirigiendo a Control Center...
      </div>
    </div>
  );
}

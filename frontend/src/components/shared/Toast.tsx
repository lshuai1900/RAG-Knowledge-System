import { useEffect, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react';
import { setToastHandler, type ToastType } from './toast';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  useEffect(() => {
    setToastHandler(addToast);
    return () => { setToastHandler(null); };
  }, [addToast]);

  const remove = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  const icon = (type: ToastType) => {
    switch (type) {
      case 'success': return <CheckCircle className="h-4 w-4 text-emerald-500" />;
      case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    }
  };

  const bg = (type: ToastType) => {
    switch (type) {
      case 'success': return 'bg-white border-emerald-200';
      case 'error': return 'bg-white border-red-200';
      case 'warning': return 'bg-white border-amber-200';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-2.5 px-4 py-3 rounded-xl border shadow-elevated text-sm animate-slide-up ${bg(t.type)}`}
        >
          <span className="flex-shrink-0 mt-0.5">{icon(t.type)}</span>
          <span className="flex-1 text-text-primary whitespace-pre-wrap text-xs leading-5">{t.message}</span>
          <button
            className="flex-shrink-0 p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-50 transition-colors"
            onClick={() => remove(t.id)}
            aria-label="关闭通知"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

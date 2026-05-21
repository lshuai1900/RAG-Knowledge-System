export type ToastType = 'success' | 'error' | 'warning';

type ToastHandler = (type: ToastType, message: string) => void;

let pushToast: ToastHandler | null = null;

export function toast(type: ToastType, message: string) {
  pushToast?.(type, message);
}

export function setToastHandler(handler: ToastHandler | null) {
  pushToast = handler;
}

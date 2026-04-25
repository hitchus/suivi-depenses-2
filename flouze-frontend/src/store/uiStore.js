import { create } from 'zustand'

let _id = 0

export const useUiStore = create((set) => ({
  toasts: [],

  toast: (message, type = 'info') => {
    const id = ++_id
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 3500)
  },

  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

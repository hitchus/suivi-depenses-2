import { create } from 'zustand'
import client from '../api/client'

export const useAuthStore = create((set, get) => ({
  user: null,
  accessToken: null,

  setAccessToken: (token) => set({ accessToken: token }),

  login: async (email, password) => {
    const { data } = await client.post('/auth/login', { email, password })
    set({ accessToken: data.access_token, user: data.user ?? null })
    // Fetch full user profile if not returned in login response
    if (!data.user) {
      try {
        const { data: me } = await client.get('/users/me')
        set({ user: me })
      } catch {
        // non-fatal
      }
    }
    return data
  },

  register: async (email, password, display_name) => {
    await client.post('/auth/register', { email, password, display_name })
    return get().login(email, password)
  },

  logout: async () => {
    try { await client.post('/auth/logout') } catch { /* ignore */ }
    set({ user: null, accessToken: null })
  },

  fetchMe: async () => {
    const { data } = await client.get('/users/me')
    set({ user: data })
    return data
  },
}))

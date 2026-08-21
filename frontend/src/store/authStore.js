/**
 * Product Detective — Auth & Billing Store
 * Zustand store for user identity, JWT token, and Pro status.
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export const useAuthStore = create(
  devtools(
    persist(
      (set, get) => ({
        // ── State ──────────────────────────────────────────────────────
        token: null,
        user: null,        // { user_id, email, name, is_pro, pro_until }
        loading: false,
        error: null,

        // ── Derived helpers ─────────────────────────────────────────────
        isLoggedIn: () => !!get().token,
        isPro: () => !!get().user?.is_pro,

        // ── Auth header ─────────────────────────────────────────────────
        authHeaders: () => {
          const { token } = get()
          return token ? { Authorization: `Bearer ${token}` } : {}
        },

        // ── Signup ──────────────────────────────────────────────────────
        signup: async (email, name, password) => {
          set({ loading: true, error: null })
          try {
            const res = await fetch(`${API_BASE}/api/v1/auth/signup`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email, name, password }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || 'Signup failed')
            set({ token: data.token, user: data.user, loading: false })
            return data
          } catch (err) {
            set({ loading: false, error: err.message })
            throw err
          }
        },

        // ── Login ───────────────────────────────────────────────────────
        login: async (email, password) => {
          set({ loading: true, error: null })
          try {
            const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email, password }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || 'Login failed')
            set({ token: data.token, user: data.user, loading: false })
            return data
          } catch (err) {
            set({ loading: false, error: err.message })
            throw err
          }
        },

        // ── Refresh profile from server ─────────────────────────────────
        refreshProfile: async () => {
          const { token } = get()
          if (!token) return
          try {
            const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
              headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) {
              if (res.status === 401) set({ token: null, user: null })
              return
            }
            const user = await res.json()
            set({ user })
          } catch {
            /* network error — keep existing state */
          }
        },

        // ── Logout ──────────────────────────────────────────────────────
        logout: () => set({ token: null, user: null, error: null }),

        // ── Set Pro (after successful payment) ───────────────────────────
        setPro: () => set((s) => ({
          user: s.user ? { ...s.user, is_pro: true } : s.user,
        })),

        // ── Clear error ─────────────────────────────────────────────────
        clearError: () => set({ error: null }),
      }),
      {
        name: 'pd-auth',
        partialize: (s) => ({ token: s.token, user: s.user }),
      }
    ),
    { name: 'ProductDetectiveAuth' }
  )
)

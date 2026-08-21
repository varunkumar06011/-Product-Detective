/**
 * Product Detective — useAuth Hook
 * Selector hooks over the auth store to avoid unnecessary re-renders.
 */

import { useAuthStore } from '../store/authStore'

export function useAuth() {
  return useAuthStore()
}

export function useUser()   { return useAuthStore((s) => s.user) }
export function useToken()  { return useAuthStore((s) => s.token) }
export function useIsPro()  { return useAuthStore((s) => !!s.user?.is_pro) }
export function useIsLoggedIn() { return useAuthStore((s) => !!s.token) }
export function useAuthLoading() { return useAuthStore((s) => s.loading) }
export function useAuthError()   { return useAuthStore((s) => s.error) }

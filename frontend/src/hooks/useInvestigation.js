/**
 * Product Detective — useInvestigation Hook
 * Thin wrapper around the Zustand store that exposes
 * only what each component needs — keeps components clean.
 */

import { useInvestigationStore, SCREENS, LOADING_STEPS } from '../store/investigationStore'

// ── Main hook ─────────────────────────────────────────────────────────────────
export function useInvestigation() {
  return useInvestigationStore()
}

// ── Selector hooks (avoids unnecessary re-renders) ────────────────────────────
export function useScreen()    { return useInvestigationStore((s) => s.screen) }
export function useVerdict()   { return useInvestigationStore((s) => s.verdict) }
export function useClueCards() { return useInvestigationStore((s) => s.clueCards) }
export function useActiveClue(){
  const activeClueId = useInvestigationStore((s) => s.activeClueId)
  const clueCards    = useInvestigationStore((s) => s.clueCards)
  return clueCards.find((c) => c.id === activeClueId) || null
}

export function useProductMeta() {
  return useInvestigationStore((s) => ({
    title:       s.productTitle,
    price:       s.productPrice,
    rating:      s.productRating,
    reviewCount: s.productReviewCount,
    category:    s.category,
  }))
}

export function useLoadingState() {
  return useInvestigationStore((s) => ({
    loading:     s.loading,
    loadingStep: s.loadingStep,
    steps:       LOADING_STEPS,
    error:       s.error,
  }))
}

export function useVerdictData() {
  return useInvestigationStore((s) => ({
    verdict:      s.verdict,
    confidence:   s.confidence,
    evidence:     s.evidence,
    alternatives: s.alternatives,
    caseNumber:   s.caseNumber,
  }))
}

// ── Exported constants ────────────────────────────────────────────────────────
export { SCREENS, LOADING_STEPS }

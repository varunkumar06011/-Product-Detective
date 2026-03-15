/**
 * Product Detective — Global Investigation State
 * Zustand store managing the entire investigation lifecycle.
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

// ── Types ──────────────────────────────────────────────────────────────────────

export const SCREENS = {
  HOME:          'HOME',
  INTERROGATION: 'INTERROGATION',
  LOADING:       'LOADING',
  BOARD:         'BOARD',
  VERDICT:       'VERDICT',
}

export const VERDICT = {
  BUY:   'BUY',
  WAIT:  'WAIT',
  AVOID: 'AVOID',
}

// ── Initial state ─────────────────────────────────────────────────────────────

const initialState = {
  // Navigation
  screen: SCREENS.HOME,
  caseNumber: '',

  // User inputs
  url: '',
  budget: '',
  purpose: '',
  priority: '',

  // Investigation results
  loading: false,
  loadingStep: 0,
  error: null,

  // Product data
  productTitle: '',
  productPrice: 0,
  productRating: 0,
  productReviewCount: 0,
  category: '',

  // Analysis results
  clueCards: [],       // Array of ClueCard objects
  activeClueId: null,

  // Decision
  verdict: null,       // 'BUY' | 'WAIT' | 'AVOID'
  confidence: 0,
  evidence: [],
  alternatives: [],
}

// ── Loading log messages (shown during investigation) ─────────────────────────

export const LOADING_STEPS = [
  '🔍 Accessing product database...',
  '📄 Scraping reviews across platforms...',
  '🧠 Running NLP sentiment pipeline...',
  '⚠️  Detecting complaint patterns...',
  '📈 Analysing complaint timeline trends...',
  '🛡️  Calculating review trust score...',
  '🔬 Evaluating product specifications...',
  '⚖️  Building case for verdict...',
]

// ── Store ─────────────────────────────────────────────────────────────────────

export const useInvestigationStore = create(
  devtools(
    (set, get) => ({
      ...initialState,

      // ── Navigation ──────────────────────────────────────────────────────────
      setScreen: (screen) => set({ screen }),

      setScreenQuiet: (screen) => set({ screen }),

      goTo: (screen) => {
        set({ screen, error: null })
        window.scrollTo({ top: 0, behavior: 'smooth' })
      },

      // ── Case management ─────────────────────────────────────────────────────
      generateCaseNumber: () => {
        const num = `PD-${Math.floor(Math.random() * 9000 + 1000)}`
        set({ caseNumber: num })
        return num
      },

      // ── User inputs ─────────────────────────────────────────────────────────
        setUrl: (url) => set({ url }),
        setBudget: (budget) => set({ budget }),
        setPurpose: (purpose) => set({ purpose }),
        setPriority: (priority) => set({ priority }),

        // ── Investigation flow ──────────────────────────────────────────────────
      startInvestigation: async () => {
        const { url, budget, purpose, priority } = get()
        if (!url || !purpose || !priority) return

        set({ loading: true, error: null, loadingStep: 0, screen: SCREENS.LOADING })

        // Simulate step progression while API call runs
        const stepTimer = setInterval(() => {
          set((state) => ({
            loadingStep: Math.min(state.loadingStep + 1, LOADING_STEPS.length - 1),
          }))
        }, 700)

        try {
          const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
          const response = await fetch(`${baseUrl}/api/v1/verdict/investigate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              url,
              budget: parseFloat(budget) || 0,
              purpose,
              priority,
            }),
          })

          if (!response.ok) {
            const err = await response.json()
            throw new Error(err.detail || 'Investigation failed')
          }

          const data = await response.json()
          clearInterval(stepTimer)

          set({
            loading: false,
            loadingStep: LOADING_STEPS.length - 1,
            screen: SCREENS.BOARD,
            productTitle:       data.product_title,
            productPrice:       data.product_price,
            productRating:      data.product_rating,
            productReviewCount: data.product_review_count,
            category:           data.category,
            clueCards:          data.clue_cards,
            verdict:            data.verdict,
            confidence:         data.confidence,
            evidence:           data.evidence,
            alternatives:       data.alternatives,
          })
        } catch (err) {
          clearInterval(stepTimer)
          set({ loading: false, error: err.message, screen: SCREENS.INTERROGATION })
        }
      },

      // Demo mode — load pre-built investigation results (no API call)
      loadDemo: (demoData) => {
        set({
          url:                demoData.url,
          productTitle:       demoData.title,
          productPrice:       demoData.price,
          productRating:      demoData.rating,
          productReviewCount: demoData.reviewCount,
          category:           demoData.category,
          clueCards:          demoData.clueCards,
          verdict:            demoData.verdict,
          confidence:         demoData.confidence,
          evidence:           demoData.evidence,
          alternatives:       demoData.alternatives,
          loading:            false,
          error:              null,
          screen:             SCREENS.LOADING,
        })

          // Simulate loading steps, then show board
          let step = 0
          const timer = setInterval(() => {
            step++
            set({ loadingStep: step })
            if (step >= LOADING_STEPS.length - 1) {
              clearInterval(timer)
              setTimeout(() => set({ screen: SCREENS.BOARD }), 400)
            }
          }, 550)
        },

      // ── Clue interaction ────────────────────────────────────────────────────
      setActiveClue: (id) => set({ activeClueId: id }),
      toggleClue: (id) => set((state) => ({
        activeClueId: state.activeClueId === id ? null : id,
      })),

      // ── Deliver verdict ─────────────────────────────────────────────────────
      deliverVerdict: () => set({ screen: SCREENS.VERDICT }),

      // ── Reset ───────────────────────────────────────────────────────────────
      reset: () => {
        const caseNumber = `PD-${Math.floor(Math.random() * 9000 + 1000)}`
        set({ ...initialState, caseNumber })
      },
    }),
    { name: 'ProductDetective' }
  )
)

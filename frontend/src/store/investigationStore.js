/**
 * Product Detective — Global Investigation State
 * Zustand store managing the entire investigation lifecycle.
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { useAuthStore } from './authStore'

// ── Types ──────────────────────────────────────────────────────────────────────

export const SCREENS = {
  HOME:          'HOME',
  INTERROGATION: 'INTERROGATION',
  LOADING:       'LOADING',
  BOARD:         'BOARD',
  VERDICT:       'VERDICT',
  PRICING:       'PRICING',
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

  // Paywall
  isPro: false,
  paywall: null,
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
        // We slow down as we get closer to 100% to avoid looking "stuck"
        const stepTimer = setInterval(() => {
          set((state) => {
            const nextStep = state.loadingStep + 1
            if (nextStep >= LOADING_STEPS.length - 1) {
              // Stay at the second to last step until API resolves
              return { loadingStep: LOADING_STEPS.length - 2 }
            }
            return { loadingStep: nextStep }
          })
        }, 800)

        try {
          const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 95000) // 95s timeout for slow scrapes

          // Include auth token if logged in (so Pro users get full results)
          const authToken = useAuthStore.getState().token
          const headers = { 'Content-Type': 'application/json' }
          if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`
          }

          const response = await fetch(`${baseUrl}/api/v1/verdict/investigate`, {
            method: 'POST',
            headers,
            signal: controller.signal,
            body: JSON.stringify({
              url,
              budget: parseFloat(budget) || 0,
              purpose,
              priority,
            }),
          })

          clearTimeout(timeoutId)

          if (!response.ok) {
            let errorMsg = 'Investigation failed'
            try {
              const err = await response.json()
              errorMsg = err.detail || errorMsg
            } catch (e) {
              errorMsg = `Server Error (${response.status})`
            }
            throw new Error(errorMsg)
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
            isPro:              data.is_pro || false,
            paywall:            data.paywall || null,
          })
        } catch (err) {
          clearInterval(stepTimer)
          const message = err.name === 'AbortError' 
            ? 'The investigation is taking too long. Amazon might be blocking our scraper or the server is overloaded. Please try again in a few minutes.'
            : err.message
          set({ loading: false, error: message, screen: SCREENS.INTERROGATION })
        }
      },

      // Demo mode — load pre-built investigation results (no API call)
      loadDemo: (demoData) => {
        // Clear any existing demo timer before starting a new one
        const existingTimer = get()._demoTimer
        if (existingTimer) clearInterval(existingTimer)

        // Demo shows full results (no paywall) so users can see what Pro offers
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
          isPro:              true,    // demo shows full unlocked experience
          paywall:            null,
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
              set({ _demoTimer: null })
              setTimeout(() => set({ screen: SCREENS.BOARD }), 400)
            }
          }, 550)
          set({ _demoTimer: timer })
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
        const existingTimer = get()._demoTimer
        if (existingTimer) clearInterval(existingTimer)
        const caseNumber = `PD-${Math.floor(Math.random() * 9000 + 1000)}`
        set({ ...initialState, caseNumber })
      },
    }),
    { name: 'ProductDetective' }
  )
)

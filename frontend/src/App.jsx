/**
 * Product Detective — App Root
 * Renders the correct screen based on global store state.
 */

import React, { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useScreen, useInvestigation, SCREENS } from './hooks/useInvestigation'
import { useInvestigationStore } from './store/investigationStore'
import Header from './components/Header/Header'
import HomePage from './pages/HomePage'
import InterrogationPage from './pages/InterrogationPage'
import LoadingBoard from './components/LoadingBoard/LoadingBoard'
import InvestigationBoard from './components/InvestigationBoard/InvestigationBoard'
import VerdictPage from './pages/VerdictPage'
import PricingPage from './pages/PricingPage'
import './styles/globals.css'

const PAGE_COMPONENTS = {
  [SCREENS.HOME]:          HomePage,
  [SCREENS.INTERROGATION]: InterrogationPage,
  [SCREENS.LOADING]:       LoadingBoard,
  [SCREENS.BOARD]:         InvestigationBoard,
  [SCREENS.VERDICT]:       VerdictPage,
  [SCREENS.PRICING]:       PricingPage,
}

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
  exit:    { opacity: 0, y: -12, transition: { duration: 0.2 } },
}

export default function App() {
  const screen = useScreen()
  const { generateCaseNumber, caseNumber } = useInvestigation()

  useEffect(() => {
    if (!caseNumber) generateCaseNumber()

    const handlePopState = (event) => {
      if (event.state && event.state.screen) {
        useInvestigationStore.getState().setScreenQuiet(event.state.screen)
      } else {
        const hash = window.location.hash.replace('#/', '').toUpperCase()
        if (SCREENS[hash]) {
          useInvestigationStore.getState().setScreenQuiet(hash)
        } else {
          useInvestigationStore.getState().setScreenQuiet(SCREENS.HOME)
        }
      }
    };

    window.addEventListener('popstate', handlePopState)
    
    // Initial sync
    const initialHash = window.location.hash.replace('#/', '').toUpperCase()
    if (SCREENS[initialHash] && initialHash !== screen) {
       useInvestigationStore.getState().setScreenQuiet(initialHash)
    } else {
       window.history.replaceState({ screen }, '', `#/${screen.toLowerCase()}`)
    }

    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Sync store -> history
  useEffect(() => {
    const currentHash = window.location.hash.replace('#/', '').toUpperCase()
    if (currentHash !== screen) {
      window.history.pushState({ screen }, '', `#/${screen.toLowerCase()}`)
    }
  }, [screen])

  const ActivePage = PAGE_COMPONENTS[screen] || HomePage

  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        <AnimatePresence mode="wait">
          <motion.div
            key={screen}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <ActivePage />
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="app-footer">
        <span className="mono">Product Detective © 2025</span>
        <span className="mono">·</span>
        <span className="mono">AI-Powered Purchase Intelligence</span>
      </footer>
    </div>
  )
}

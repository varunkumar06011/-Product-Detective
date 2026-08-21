/**
 * Product Detective — Header Component
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useInvestigation, SCREENS } from '../../hooks/useInvestigation'
import { useAuth, useIsLoggedIn, useIsPro } from '../../hooks/useAuth'
import AuthModal from '../AuthModal/AuthModal'
import PaymentModal from '../PaymentModal/PaymentModal'
import styles from './Header.module.css'

export default function Header() {
  const { caseNumber, screen, goTo } = useInvestigation()
  const isLoggedIn = useIsLoggedIn()
  const isPro = useIsPro()
  const { logout, refreshProfile } = useAuth()
  const [authOpen, setAuthOpen] = useState(false)
  const [payOpen, setPayOpen] = useState(false)

  // Refresh profile once on mount if logged in (syncs Pro status)
  useEffect(() => {
    if (isLoggedIn) refreshProfile()
  }, [])

  return (
    <>
      <header className={styles.header}>
        <div className={styles.inner}>
          <div className={styles.confidential}>— CONFIDENTIAL —</div>

          <div className={styles.logoRow}>
            <motion.div
              className={styles.logoIcon}
              animate={{ rotate: [0, -5, 5, 0], scale: [1, 1.1, 1.1, 1] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            >
              🕵️‍♂️🔍
            </motion.div>
            <h1 className={styles.title}>
              Product <span className={styles.accent}>Detective</span>
            </h1>
          </div>

          <p className={styles.subtitle}>
            AI-Powered Purchase Intelligence · Est. 2025
          </p>

          <div className={styles.caseTag}>
            <span className={styles.caseLabel}>CASE NO.</span>
            <strong className={styles.caseNumber}>{caseNumber}</strong>
          </div>

          {/* Auth + Upgrade buttons */}
          <div className={styles.authRow}>
            <button
              className={`${styles.navLink} ${screen === SCREENS.PRICING ? styles.navActive : ''}`}
              onClick={() => goTo(SCREENS.PRICING)}
            >
              Pricing
            </button>

            {isLoggedIn ? (
              <>
                {isPro ? (
                  <span className={styles.proBadge}>PRO</span>
                ) : (
                  <button
                    className={styles.upgradeBtn}
                    onClick={() => setPayOpen(true)}
                  >
                    Go Pro
                  </button>
                )}
                <button className={styles.logoutBtn} onClick={logout}>
                  Logout
                </button>
              </>
            ) : (
              <button
                className={styles.loginBtn}
                onClick={() => setAuthOpen(true)}
              >
                Login
              </button>
            )}
          </div>
        </div>
      </header>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      <PaymentModal open={payOpen} onClose={() => setPayOpen(false)} />
    </>
  )
}

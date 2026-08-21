/**
 * Product Detective — Pricing Page
 * Shows Free vs Pro tiers with a CTA to upgrade.
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth, useIsPro, useIsLoggedIn } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import { useInvestigation, SCREENS } from '../hooks/useInvestigation'
import PaymentModal from '../components/PaymentModal/PaymentModal'
import AuthModal from '../components/AuthModal/AuthModal'
import styles from './PricingPage.module.css'

export default function PricingPage() {
  const isPro = useIsPro()
  const isLoggedIn = useIsLoggedIn()
  const { logout } = useAuth()
  const { goTo } = useInvestigation()
  const [payOpen, setPayOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [pendingUpgrade, setPendingUpgrade] = useState(false)

  const handleUpgrade = () => {
    if (!isLoggedIn) {
      setPendingUpgrade(true)  // after login, auto-open payment
      setAuthOpen(true)
    } else {
      setPayOpen(true)
    }
  }

  const handleAuthClose = () => {
    setAuthOpen(false)
    // If login succeeded and user wanted to upgrade, open payment modal
    if (pendingUpgrade && useAuthStore.getState().token) {
      setPayOpen(true)
    }
    setPendingUpgrade(false)
  }

  return (
    <motion.div
      className={styles.page}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className={styles.heading}>
        <span className="label">◈ PRICING</span>
        <h1 className={styles.title}>Choose Your Clearance Level</h1>
        <p className={styles.subtitle}>
          Free gets you the verdict. Pro gets you the full case file.
        </p>
      </div>

      <div className={styles.tiers}>
        {/* Free tier */}
        <div className={`${styles.tier} ${styles.tierFree}`}>
          <div className={styles.tierName}>FREE</div>
          <div className={styles.tierPrice}>₹0</div>
          <div className={styles.tierPeriod}>forever</div>
          <ul className={styles.tierFeatures}>
            <li>✓ BUY / WAIT / AVOID verdict</li>
            <li>✓ Confidence score</li>
            <li>✓ Product meta (price, rating, category)</li>
            <li>✓ 2 evidence preview points</li>
            <li className={styles.muted}>✗ Full evidence breakdown</li>
            <li className={styles.muted}>✗ Complaint cluster analysis</li>
            <li className={styles.muted}>✗ Alternative recommendations</li>
          </ul>
          <button
            className="btn-secondary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={() => goTo(SCREENS.HOME)}
          >
            Start Investigating
          </button>
        </div>

        {/* Pro tier */}
        <div className={`${styles.tier} ${styles.tierPro}`}>
          <div className={styles.badge}>RECOMMENDED</div>
          <div className={styles.tierName}>PRO</div>
          <div className={styles.tierPrice}>₹99</div>
          <div className={styles.tierPeriod}>/ year</div>
          <ul className={styles.tierFeatures}>
            <li>✓ Everything in Free</li>
            <li>✓ Full evidence breakdown</li>
            <li>✓ Complaint cluster analysis & timelines</li>
            <li>✓ Better alternative recommendations</li>
            <li>✓ Review trust & fake-review details</li>
            <li>✓ Unlimited investigations</li>
          </ul>
          {isPro ? (
            <button className="btn-secondary" disabled style={{ width: '100%', justifyContent: 'center', opacity: 0.7 }}>
              ✓ Pro Active
            </button>
          ) : (
            <button
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleUpgrade}
            >
              {isLoggedIn ? 'Upgrade to Pro →' : 'Login to Upgrade →'}
            </button>
          )}
        </div>
      </div>

      {isLoggedIn && (
        <div className={styles.accountRow}>
          <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>
            Logged in · {isPro ? 'Pro member' : 'Free member'}
          </span>
          <button className="btn-secondary" onClick={logout}>Logout</button>
        </div>
      )}

      <PaymentModal open={payOpen} onClose={() => setPayOpen(false)} />
      <AuthModal open={authOpen} onClose={handleAuthClose} mode="login" />
    </motion.div>
  )
}

/**
 * Product Detective — Verdict Page
 * The final "CASE CLOSED" screen with evidence summary,
 * alternatives preview, and action buttons.
 */

import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useVerdictData, useProductMeta, useInvestigation, SCREENS } from '../hooks/useInvestigation'
import { useIsPro, useIsLoggedIn } from '../hooks/useAuth'
import { useAuthStore } from '../store/authStore'
import VerdictStamp from '../components/VerdictStamp/VerdictStamp'
import PaymentModal from '../components/PaymentModal/PaymentModal'
import AuthModal from '../components/AuthModal/AuthModal'
import styles from './VerdictPage.module.css'

export default function VerdictPage() {
  const { verdict, confidence, evidence, alternatives, caseNumber, isPro: resultIsPro, paywall } = useVerdictData()
  const { title, price, category } = useProductMeta()
  const { goTo, reset } = useInvestigation()
  const isPro = useIsPro()
  const isLoggedIn = useIsLoggedIn()
  const [payOpen, setPayOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [pendingUpgrade, setPendingUpgrade] = useState(false)

  // Use the paywall field from the API response (authoritative source)
  const locked = paywall?.locked === true

  const handleUnlock = () => {
    if (isLoggedIn) {
      setPayOpen(true)
    } else {
      setPendingUpgrade(true)
      setAuthOpen(true)
    }
  }

  const handleAuthClose = () => {
    setAuthOpen(false)
    if (pendingUpgrade && useAuthStore.getState().token) {
      setPayOpen(true)
    }
    setPendingUpgrade(false)
  }

  useEffect(() => {
    if (!verdict) {
      goTo(SCREENS.HOME)
    }
  }, [verdict, goTo])

  if (!verdict) {
    return null
  }

  const verdictColor = { BUY: 'var(--green)', WAIT: 'var(--gold)', AVOID: 'var(--red)' }[verdict]

  const handleShare = async () => {
    const text = `Product Detective verdict on "${title}": ${verdict} (${confidence}% confidence)\nCase: ${caseNumber}`
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Product Detective Report', text })
      } catch {
        /* user cancelled share dialog */
      }
    } else {
      try {
        await navigator.clipboard.writeText(text)
        alert('Report summary copied to clipboard!')
      } catch {
        alert('Could not copy to clipboard. Please copy manually:\n\n' + text)
      }
    }
  }

  return (
    <motion.div
      className={styles.page}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      {/* Main verdict card */}
      <div
        className={styles.verdictCard}
        style={{ borderColor: verdictColor }}
      >
        {/* Corner stamp */}
        <div className={styles.caseClosedStamp}>CASE CLOSED</div>

        <VerdictStamp verdict={verdict} confidence={confidence} caseNumber={caseNumber} />

        <hr className="divider" style={{ margin: '4px 0 20px' }} />

        {/* Evidence summary */}
        <div className={styles.evidenceBox}>
          <div className="label" style={{ marginBottom: 10 }}>◈ EVIDENCE SUMMARY</div>
          {evidence && evidence.map((e, i) => (
            <motion.div
              key={i}
              className={styles.evidencePoint}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.07 }}
            >
              <span className={styles.arrow}>→</span>
              {e}
            </motion.div>
          ))}
        </div>

        {/* Alternatives mini-preview */}
        {alternatives && alternatives.length > 0 && verdict !== 'BUY' && (
          <motion.div
            className={styles.altsPreview}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <div className="label" style={{ marginBottom: 10 }}>◈ BETTER OPTIONS FOUND</div>
            {alternatives.slice(0, 2).map((alt, i) => (
              <div key={i} className={styles.altRow}>
                <span className={styles.altRank}>{alt.rank || `0${i + 1}`}</span>
                <div>
                  <div className={styles.altName}>{alt.name}</div>
                  <div className={styles.altReason}>
                    {alt.reasons?.[0] || alt.why_better}
                  </div>
                </div>
                {alt.price && (
                  <div className={styles.altPrice}>
                    ₹{Number(alt.price).toLocaleString('en-IN')}
                  </div>
                )}
              </div>
            ))}
          </motion.div>
        )}

        {/* Paywall overlay for free users */}
        {locked && (
          <motion.div
            className={styles.paywall}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.75 }}
          >
            <div className={styles.paywallIcon}>🔒</div>
            <div className={styles.paywallTitle}>Case File Partially Sealed</div>
            <p className={styles.paywallText}>
              You've seen the verdict. Unlock the <strong>full evidence breakdown</strong>,
              complaint analysis, and better alternatives with <strong>Pro</strong>.
            </p>
            <button
              className="btn-primary"
              style={{ justifyContent: 'center', marginTop: 8 }}
              onClick={handleUnlock}
            >
              {isLoggedIn ? 'Unlock with Pro · ₹99 →' : 'Login to Unlock →'}
            </button>
            <button
              className={styles.paywallLink}
              onClick={() => goTo(SCREENS.PRICING)}
            >
              See what's included
            </button>
          </motion.div>
        )}

        {/* Action buttons */}
        <motion.div
          className={styles.actions}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          <button
            className="btn-primary"
            style={{ flex: '0 1 auto' }}
            onClick={handleShare}
          >
            ↗ Share Report
          </button>
          <button
            className="btn-secondary"
            onClick={() => goTo(SCREENS.BOARD)}
          >
            ← Review Clues
          </button>
          <button
            className="btn-secondary"
            onClick={reset}
          >
            + New Case
          </button>
        </motion.div>
      </div>

      {/* Product meta footer */}
      <div className={styles.footer}>
        <span>{title}</span>
        {price > 0 && <span>₹{price.toLocaleString('en-IN')}</span>}
        {category && <span>{category}</span>}
      </div>

      <PaymentModal open={payOpen} onClose={() => setPayOpen(false)} />
      <AuthModal open={authOpen} onClose={handleAuthClose} mode="login" />
    </motion.div>
  )
}

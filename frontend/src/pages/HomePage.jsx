/**
 * Product Detective — Home Page
 * URL input and demo product cards.
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useInvestigation, SCREENS } from '../hooks/useInvestigation'
import { DEMOS } from '../utils/demoData'
import styles from './HomePage.module.css'

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}
const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
}

export default function HomePage() {
  const { setUrl, goTo, loadDemo, generateCaseNumber } = useInvestigation()
  const [urlValue, setUrlValue] = useState('')
  const [urlError, setUrlError] = useState('')

  const handleSubmit = () => {
    const trimmed = urlValue.trim()
    if (!trimmed) { setUrlError('Please paste a product URL'); return }
    if (!trimmed.startsWith('http')) { setUrlError('URL must start with https://'); return }
    setUrlError('')
    setUrl(trimmed)
    generateCaseNumber()
    goTo(SCREENS.INTERROGATION)
  }

  const handleDemo = (key) => {
    generateCaseNumber()
    loadDemo(DEMOS[key])
  }

  return (
    <motion.div
      className={styles.page}
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* URL input card */}
      <motion.div className="card" variants={item}>
        <div className="label" style={{ marginBottom: 12 }}>◈ OPEN A CASE</div>
        <h2 className={styles.cardTitle}>Submit a Product for Investigation</h2>
        <p className={styles.cardSub}>
          Paste any Amazon or Flipkart product URL. We'll dig through the reviews
          and tell you the truth.
        </p>

        <div className={styles.urlRow}>
          <input
            className={styles.urlInput}
            type="url"
            placeholder="https://www.amazon.in/dp/..."
            value={urlValue}
            onChange={(e) => { setUrlValue(e.target.value); setUrlError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <button className="btn-primary" onClick={handleSubmit}>
            🔎 FILE CASE
          </button>
        </div>

        {urlError && <p className={styles.urlError}>{urlError}</p>}

        <p className={styles.urlHint}>
          Supported platforms:{' '}
          <span className={styles.platform}>Amazon.in</span>{' · '}
          <span className={styles.platform}>Amazon.com</span>{' · '}
          <span className={styles.platform}>Flipkart</span>
        </p>
      </motion.div>

      {/* Demo divider */}
      <motion.div className={styles.demoLabel} variants={item}>
        <span>— or try a demo investigation —</span>
      </motion.div>

      {/* Demo cards */}
      <motion.div className={styles.demoGrid} variants={container}>
        {Object.values(DEMOS).map((demo) => (
          <motion.div
            key={demo.id}
            className={styles.demoCard}
            variants={item}
            whileHover={{ y: -3, boxShadow: '3px 5px 0 rgba(28,26,20,0.15)' }}
            onClick={() => handleDemo(demo.id)}
          >
            <div className={styles.demoIcon}>{demo.icon}</div>
            <div className={styles.demoType} style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-3)', letterSpacing: 2 }}>
              TRY DEMO
            </div>
            <div className={styles.demoName}>{demo.label}</div>
            <div className={styles.demoPrice} style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: 'var(--ink-3)', marginTop: 4 }}>
              ₹{demo.price.toLocaleString()} · ★ {demo.rating}
            </div>
            <VerdictPill verdict={demo.verdict} />
          </motion.div>
        ))}
      </motion.div>

      {/* Feature highlights */}
      <motion.div className={styles.features} variants={container}>
        {[
          { icon: '💬', title: 'Sentiment Analysis', desc: 'NLP on every review — not just star ratings' },
          { icon: '📈', title: 'Complaint Trends', desc: 'Detect rising defect patterns before you buy' },
          { icon: '🛡️', title: 'Trust Scoring', desc: 'Spot fake and manipulated review campaigns' },
          { icon: '⚖️', title: 'Clear Verdict', desc: 'BUY · WAIT · AVOID with full reasoning' },
        ].map((f) => (
          <motion.div key={f.title} className={styles.featureItem} variants={item}>
            <span className={styles.featureIcon}>{f.icon}</span>
            <div>
              <div className={styles.featureTitle}>{f.title}</div>
              <div className={styles.featureDesc}>{f.desc}</div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  )
}

function VerdictPill({ verdict }) {
  const colors = {
    BUY:   { bg: 'rgba(42,107,60,0.12)',  color: 'var(--green)' },
    WAIT:  { bg: 'rgba(200,151,58,0.15)', color: 'var(--gold)'  },
    AVOID: { bg: 'rgba(184,50,36,0.12)',  color: 'var(--red)'   },
  }
  const style = colors[verdict] || colors.WAIT
  return (
    <div style={{
      marginTop: 10, display: 'inline-block',
      background: style.bg, color: style.color,
      fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600,
      letterSpacing: 2, padding: '4px 11px', borderRadius: 10,
    }}>
      {verdict}
    </div>
  )
}

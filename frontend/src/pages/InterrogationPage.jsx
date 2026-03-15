/**
 * Product Detective — Interrogation Page
 * Collects budget, purpose, and priority from the user.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useInvestigation, SCREENS } from '../hooks/useInvestigation'
import styles from './InterrogationPage.module.css'

const PURPOSE_OPTIONS   = ['Gaming', 'Daily Use', 'Content Creation', 'Work / Office', 'Student']
const PRIORITY_OPTIONS  = ['Performance', 'Durability', 'Best Price', 'Battery Life', 'Brand Trust']

export default function InterrogationPage() {
  const {
    url, budget, purpose, priority,
    setBudget, setPurpose, setPriority,
    startInvestigation, goTo, error,
  } = useInvestigation()

  const canStart = purpose && priority

  return (
    <motion.div
      className={styles.page}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="card">
        <div className="label" style={{ marginBottom: 12 }}>◈ WITNESS INTERROGATION</div>
        <h2 className={styles.title}>Three Questions. Honest Answers.</h2>
        <p className={styles.sub}>
          Tell the detective what you need. We'll match the evidence to your situation.
        </p>

        {url && (
          <div className={styles.urlPreview}>
            <span className={styles.urlLabel}>INVESTIGATING:</span>
            <span className={styles.urlText}>{url.length > 60 ? url.slice(0, 60) + '…' : url}</span>
          </div>
        )}

        <hr className="divider" />

        {/* Q1 — Budget */}
        <div className={styles.qGroup}>
          <label className={styles.qLabel}>
            <span className={styles.qNum}>Q.01</span> — What's your budget? (₹)
          </label>
          <input
            className={styles.budgetInput}
            type="number"
            placeholder="e.g. 45000"
            min="0"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
          <span className={styles.qHint}>Optional — helps us flag overpriced products</span>
        </div>

        {/* Q2 — Purpose */}
        <div className={styles.qGroup}>
          <label className={styles.qLabel}>
            <span className={styles.qNum}>Q.02</span> — Primary purpose? <span className={styles.required}>*</span>
          </label>
          <div className={styles.pillGroup}>
            {PURPOSE_OPTIONS.map((opt) => (
              <motion.button
                key={opt}
                className={`${styles.pill} ${purpose === opt ? styles.pillSelected : ''}`}
                onClick={() => setPurpose(opt)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
              >
                {opt}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Q3 — Priority */}
        <div className={styles.qGroup}>
          <label className={styles.qLabel}>
            <span className={styles.qNum}>Q.03</span> — Top priority? <span className={styles.required}>*</span>
          </label>
          <div className={styles.pillGroup}>
            {PRIORITY_OPTIONS.map((opt) => (
              <motion.button
                key={opt}
                className={`${styles.pill} ${priority === opt ? styles.pillSelected : ''}`}
                onClick={() => setPriority(opt)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
              >
                {opt}
              </motion.button>
            ))}
          </div>
        </div>

        {error && (
          <div className="alert danger" style={{ marginBottom: 16 }}>
            <span className="alert-icon">⚠</span>
            {error}
          </div>
        )}

        <div className={styles.actions}>
          <button
            className="btn-secondary"
            onClick={() => goTo(SCREENS.HOME)}
            style={{ padding: '11px 18px' }}
          >
            ← Back
          </button>
          <motion.button
            className="btn-primary"
            style={{ flex: 1, justifyContent: 'center', fontSize: 13 }}
            onClick={startInvestigation}
            disabled={!canStart}
            whileTap={{ scale: 0.97 }}
          >
            🕵️ BEGIN INVESTIGATION
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

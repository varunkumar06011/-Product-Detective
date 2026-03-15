/**
 * Product Detective — VerdictStamp Component
 * Animated dramatic stamp reveal for the final verdict.
 */

import React from 'react'
import { motion } from 'framer-motion'
import styles from './VerdictStamp.module.css'

const VERDICT_CONFIG = {
  BUY: {
    emoji: '🟢',
    color: 'var(--green)',
    bg: 'rgba(42,107,60,0.08)',
    border: 'var(--green)',
    subtext: 'The evidence supports this purchase.',
  },
  WAIT: {
    emoji: '🟡',
    color: 'var(--gold)',
    bg: 'rgba(200,151,58,0.10)',
    border: 'var(--gold)',
    subtext: 'Hold off — a better option or timing exists.',
  },
  AVOID: {
    emoji: '🔴',
    color: 'var(--red)',
    bg: 'rgba(184,50,36,0.08)',
    border: 'var(--red)',
    subtext: 'The investigation concludes: do not buy this.',
  },
}

export default function VerdictStamp({ verdict, confidence, caseNumber }) {
  const config = VERDICT_CONFIG[verdict] || VERDICT_CONFIG.WAIT

  return (
    <div className={styles.wrapper}>
      {/* Seal emoji */}
      <motion.div
        className={styles.seal}
        initial={{ scale: 0.3, rotate: -20, opacity: 0 }}
        animate={{ scale: 1, rotate: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 18, delay: 0.1 }}
      >
        {config.emoji}
      </motion.div>

      {/* Label */}
      <div className={styles.label}>INVESTIGATION COMPLETE — FINAL RULING</div>

      {/* The verdict word */}
      <motion.div
        className={styles.verdict}
        style={{ color: config.color }}
        initial={{ scale: 1.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 16, delay: 0.25 }}
      >
        {verdict}
      </motion.div>

      {/* Confidence + case number */}
      <motion.div
        className={styles.meta}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.45 }}
      >
        Confidence: {confidence}% · Case: {caseNumber}
      </motion.div>

      {/* Subtext */}
      <motion.p
        className={styles.subtext}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.55 }}
      >
        {config.subtext}
      </motion.p>
    </div>
  )
}

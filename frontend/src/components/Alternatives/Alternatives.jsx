/**
 * Product Detective — Alternatives Component
 * Displays better product recommendations when verdict is WAIT or AVOID.
 */

import React from 'react'
import { motion } from 'framer-motion'
import styles from './Alternatives.module.css'

export default function Alternatives({ alternatives }) {
  if (!alternatives || alternatives.length === 0) return null

  return (
    <div className={styles.section}>
      <div className="label" style={{ marginBottom: 12 }}>◈ BETTER SUSPECTS IDENTIFIED</div>
      <div className={styles.header}>
        <h3 className={styles.title}>Consider These Alternatives</h3>
        <p className={styles.sub}>
          Ranked by overall score, trust rating, and complaint frequency
        </p>
      </div>

      <div className={styles.list}>
        {alternatives.map((alt, i) => (
          <motion.div
            key={alt.rank || i}
            className={styles.altCard}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08, duration: 0.35 }}
          >
            <div className={styles.rank}>{alt.rank || `0${i + 1}`}</div>

            <div className={styles.altContent}>
              <div className={styles.altName}>{alt.name}</div>

              <div className={styles.altMeta}>
                {alt.price && (
                  <span className={styles.metaPill}>
                    ₹{Number(alt.price).toLocaleString('en-IN')}
                  </span>
                )}
                {alt.avg_rating && (
                  <span className={styles.metaPill}>★ {alt.avg_rating}</span>
                )}
                {alt.trust_score && (
                  <span className={styles.metaPill}>Trust {alt.trust_score}/100</span>
                )}
                {alt.score && (
                  <span className={`${styles.metaPill} ${styles.scorePill}`}>
                    Score {alt.score}/100
                  </span>
                )}
              </div>

              {alt.reasons && (
                <ul className={styles.reasons}>
                  {alt.reasons.map((r, j) => (
                    <li key={j} className={styles.reason}>
                      <span className={styles.bullet}>→</span>
                      {r}
                    </li>
                  ))}
                </ul>
              )}

              {alt.why_better && (
                <div className={styles.whyBetter}>{alt.why_better}</div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

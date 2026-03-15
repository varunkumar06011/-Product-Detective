/**
 * Product Detective — Loading Board
 * Animated loading screen shown during investigation.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useLoadingState, LOADING_STEPS } from '../../hooks/useInvestigation'
import styles from './LoadingBoard.module.css'

export default function LoadingBoard() {
  const { loadingStep } = useLoadingState()

  return (
    <div className={styles.page}>
      <div className="card">
        <div className={styles.inner}>
          <h3 className={styles.title}>Investigating product clues...</h3>
          <p className={styles.subtitle}>The detective is building your case. Stay calm.</p>

          {/* Log lines */}
          <div className={styles.log}>
            {LOADING_STEPS.map((step, i) => (
              <motion.div
                key={i}
                className={`${styles.logLine} ${i <= loadingStep ? styles.visible : styles.hidden}`}
                initial={{ opacity: 0, x: -8 }}
                animate={i <= loadingStep ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.3 }}
              >
                <span className={styles.logDot} />
                {step}
              </motion.div>
            ))}
          </div>

          {/* Progress bar */}
          <div className={styles.progressTrack}>
            <motion.div
              className={styles.progressFill}
              animate={{ width: `${((loadingStep + 1) / LOADING_STEPS.length) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className={styles.progressLabel}>
            {Math.round(((loadingStep + 1) / LOADING_STEPS.length) * 100)}% complete
          </div>
        </div>
      </div>
    </div>
  )
}

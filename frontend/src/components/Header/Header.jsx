/**
 * Product Detective — Header Component
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useInvestigation } from '../../hooks/useInvestigation'
import styles from './Header.module.css'

export default function Header() {
  const { caseNumber, screen } = useInvestigation()

  return (
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
      </div>
    </header>
  )
}

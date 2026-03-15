/**
 * Product Detective — ClueCard Component
 * Interactive evidence card with animated detail reveal panel.
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import styles from './ClueCard.module.css'

// ── Card grid ──────────────────────────────────────────────────────────────────
export function ClueGrid({ clueCards, activeClueId, onToggle }) {
  return (
    <div className={styles.grid}>
      {clueCards.map((card) => (
        <ClueCard
          key={card.id}
          card={card}
          isActive={activeClueId === card.id}
          onToggle={() => onToggle(card.id)}
        />
      ))}
    </div>
  )
}

// ── Individual card ────────────────────────────────────────────────────────────
export function ClueCard({ card, isActive, onToggle }) {
  return (
    <motion.div
      className={`${styles.card} ${styles[card.stamp]} ${isActive ? styles.active : ''}`}
      onClick={onToggle}
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.97 }}
      layout
    >
      <div className={`stamp ${card.stamp}`}>{card.tag}</div>
      <div className={styles.icon}>{card.icon}</div>
      <div className={styles.title}>{card.title}</div>
      <div className={styles.preview}>{card.preview}</div>
      <div className={styles.revealLabel}>
        {isActive ? '▼ Hide clue' : '▶ Reveal clue'}
      </div>
    </motion.div>
  )
}

// ── Detail panel (revealed below cards) ───────────────────────────────────────
export function ClueDetail({ card, onClose }) {
  if (!card) return null
  const d = card.detail

  return (
    <AnimatePresence>
      <motion.div
        className={styles.detail}
        initial={{ opacity: 0, y: -14, height: 0 }}
        animate={{ opacity: 1, y: 0, height: 'auto' }}
        exit={{ opacity: 0, y: -10, height: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className={styles.detailHeader}>
          <h3 className={styles.detailTitle}>{card.icon} {card.title}</h3>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        <div className={styles.evidenceTag}>◈ {d.label}</div>

        {/* Score circle */}
        {d.score && (
          <div className={styles.scoreRow}>
            <div className={`score-circle ${d.score.type}`}>
              <span className="score-num">{d.score.value}</span>
              <span className="score-sub">{d.score.label}</span>
            </div>
            <div className={styles.scoreNote}>
              Review trust score indicates the<br />
              authenticity of all user reviews.
            </div>
          </div>
        )}

        {/* Bars */}
        {d.bars && d.bars.map((b) => (
          <div className="bar-row" key={b.label}>
            <div className="bar-label">{b.label}</div>
            <div className="bar-track">
              <motion.div
                className={`bar-fill ${b.type}`}
                initial={{ width: 0 }}
                animate={{ width: `${b.pct}%` }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <div className="bar-pct">{b.pct}%</div>
          </div>
        ))}

        {/* Topic tags */}
        {d.tags && (
          <div className={styles.tagsRow}>
            {d.tags.map((t, i) => (
              <span key={i} className={`tag ${d.tagTypes?.[i] || 'neutral'}`}>{t}</span>
            ))}
          </div>
        )}

        {/* Timeline */}
        {d.timeline && d.timeline.length > 0 && (
          <div className="timeline" style={{ margin: '14px 0' }}>
            {d.timeline.map((t, i) => (
              <motion.div
                key={i}
                className="tl-item"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07 }}
              >
                <div className={`tl-dot ${t.type}`} />
                <div className="tl-date">{t.date}</div>
                <div className="tl-text">
                  {t.text} —{' '}
                  <span className={`tl-pct ${t.type}`}>{t.pct}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Alert */}
        {d.alert && (
          <div className={`alert ${d.alert.type}`} style={{ marginTop: 14 }}>
            <span className="alert-icon">
              {d.alert.type === 'danger' ? '⚠' : d.alert.type === 'success' ? '✓' : 'ℹ'}
            </span>
            {d.alert.text}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

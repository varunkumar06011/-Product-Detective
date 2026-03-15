/**
 * Product Detective — Investigation Board
 * The central UI: product meta, clue cards, alternatives, and verdict trigger.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useInvestigation, SCREENS } from '../../hooks/useInvestigation'
import { ClueGrid, ClueDetail } from '../ClueCard/ClueCard'
import Alternatives from '../Alternatives/Alternatives'
import styles from './InvestigationBoard.module.css'

export default function InvestigationBoard() {
  const {
    productTitle, productPrice, productRating,
    productReviewCount, category,
    clueCards, activeClueId, toggleClue,
    verdict, alternatives,
    goTo, reset,
  } = useInvestigation()

  const handleDeliverVerdict = () => {
    goTo(SCREENS.VERDICT)
  }

  const activeCard = clueCards.find((c) => c.id === activeClueId) || null

  const formatPrice = (p) =>
    p ? `₹${p.toLocaleString('en-IN')}` : '—'

  return (
    <motion.div
      className={styles.page}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      {/* Board header */}
      <div className={styles.boardHeader}>
        <div>
          <div className="label" style={{ marginBottom: 8 }}>◈ CASE EVIDENCE BOARD</div>
          <h2 className={styles.boardTitle}>{productTitle || 'Investigation Board'}</h2>
          <p className={styles.boardSub}>
            Click each clue card to reveal the detective's findings
          </p>
        </div>
        <button
          className="btn-secondary"
          style={{ fontSize: 11, padding: '8px 14px', whiteSpace: 'nowrap' }}
          onClick={reset}
        >
          Close Case ×
        </button>
      </div>

      {/* Product meta strip */}
      <div className={styles.metaStrip}>
        <MetaItem label="PRICE"   value={formatPrice(productPrice)} />
        <MetaItem label="RATING"  value={`★ ${productRating}`} />
        <MetaItem label="REVIEWS" value={productReviewCount?.toLocaleString()} />
        <MetaItem label="CATEGORY" value={category} />
      </div>

      {/* Step tracker */}
      <StepTracker clueCards={clueCards} activeClueId={activeClueId} />

      {/* Clue grid */}
      <div className="label" style={{ marginBottom: 12 }}>◈ EVIDENCE CLUES — CLICK TO REVEAL</div>
      <ClueGrid
        clueCards={clueCards}
        activeClueId={activeClueId}
        onToggle={(id) => toggleClue(id)}
      />

      {/* Detail panel — rendered below grid */}
      {activeCard && (
        <ClueDetail
          card={activeCard}
          onClose={() => toggleClue(activeClueId)}
        />
      )}

      {/* Alternatives */}
      {alternatives && alternatives.length > 0 && (
        <Alternatives alternatives={alternatives} />
      )}

      {/* Verdict CTA */}
      <div className={styles.verdictCta}>
        <motion.button
          className="btn-primary"
          style={{ padding: '14px 36px', fontSize: 14 }}
          onClick={handleDeliverVerdict}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          ⚖️ DELIVER THE VERDICT
        </motion.button>
        <p className={styles.ctaHint}>
          Explore all clues first for the full picture
        </p>
      </div>

    </motion.div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function MetaItem({ label, value }) {
  return (
    <div className={styles.metaItem}>
      <span className={styles.metaLabel}>{label}</span>
      <span className={styles.metaValue}>{value || '—'}</span>
    </div>
  )
}

function StepTracker({ clueCards, activeClueId }) {
  const revealedIds = activeClueId ? [activeClueId] : []
  return (
    <div className={styles.stepTracker}>
      {clueCards.map((card, i) => {
        const isActive = card.id === activeClueId
        return (
          <div
            key={card.id}
            className={`${styles.step} ${isActive ? styles.stepActive : ''}`}
          >
            <span className={styles.stepNum}>{String(i + 1).padStart(2, '0')}</span>
            {card.title.split(' ')[0]}
          </div>
        )
      })}
      <div className={styles.step} style={{ opacity: 0.5 }}>
        <span className={styles.stepNum}>⚖</span>Verdict
      </div>
    </div>
  )
}

/**
 * Product Detective — Payment Modal
 * Triggers Razorpay checkout for the Pro plan.
 * Expects the Razorpay checkout.js script to be loaded in index.html.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../hooks/useAuth'
import styles from './PaymentModal.module.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function PaymentModal({ open, onClose, onSuccess }) {
  const { token, user, setPro, refreshProfile } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handlePay = async () => {
    if (!token) {
      setError('Please log in first.')
      return
    }
    if (!window.Razorpay) {
      setError('Payment gateway failed to load. Please check your internet connection and try again.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      // 1. Create order on backend
      const res = await fetch(`${API_BASE}/api/v1/payments/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })
      const order = await res.json()
      if (!res.ok) throw new Error(order.detail || 'Could not create order')

      // 2. Open Razorpay checkout
      //    loading stays true while the checkout modal is open;
      //    it's cleared on dismiss, success, or failure.
      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'Product Detective',
        description: 'Pro Plan — Full Investigations (1 year)',
        order_id: order.order_id,
        prefill: {
          email: order.user_email,
          name: order.user_name || '',
        },
        method: {
          upi: true,
          card: true,
          netbanking: true,
          wallet: true,
        },
        config: {
          display: {
            blocks: {
              upi: {
                name: 'Pay using UPI',
                instruments: [
                  { method: 'upi', flows: ['collect', 'intent'] },
                ],
              },
              cards: {
                name: 'Pay using Card',
                instruments: [
                  { method: 'card' },
                ],
              },
              other: {
                name: 'Other Methods',
                instruments: [
                  { method: 'netbanking' },
                  { method: 'wallet' },
                ],
              },
            },
            sequence: ['upi', 'cards', 'other'],
            preferences: {
              show_default_blocks: true,
            },
          },
        },
        theme: { color: '#1C1A14' },
        handler: async (response) => {
          // 3. Verify payment on backend
          try {
            const vres = await fetch(`${API_BASE}/api/v1/payments/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            })
            const vdata = await vres.json()
            if (!vres.ok) throw new Error(vdata.detail || 'Verification failed')
            setPro()
            await refreshProfile()
            setLoading(false)
            onSuccess && onSuccess(vdata)
            onClose()
          } catch (err) {
            setLoading(false)
            setError('Payment succeeded but verification failed: ' + err.message)
          }
        },
        modal: {
          ondismiss: () => {
            setLoading(false)
          },
        },
      })
      rzp.on('payment.failed', (resp) => {
        setError(resp.error?.description || 'Payment failed. Please try again.')
        setLoading(false)
      })
      rzp.open()
      // NOTE: do NOT setLoading(false) here — the Razorpay modal is still
      // open asynchronously. Loading is cleared in the handlers above.
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className={styles.modal}
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ duration: 0.25 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.header}>
              <span className="label">◈ GO PRO</span>
              <button className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
            </div>

            <h2 className={styles.title}>Unlock Full Investigations</h2>

            <div className={styles.priceRow}>
              <span className={styles.price}>₹99</span>
              <span className={styles.period}>/ year</span>
            </div>

            <ul className={styles.features}>
              <li>→ Full evidence breakdown on every case</li>
              <li>→ Complaint cluster analysis & timelines</li>
              <li>→ Better alternative product recommendations</li>
              <li>→ Review trust & fake-review detection details</li>
              <li>→ Unlimited investigations</li>
            </ul>

            {!user && (
              <div className={styles.notice}>
                Please log in before upgrading.
              </div>
            )}

            {error && <div className={styles.error}>{error}</div>}

            <button
              className="btn-primary"
              disabled={loading || !user}
              onClick={handlePay}
              style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
            >
              {loading ? 'Processing...' : user ? 'Pay ₹99 with Razorpay →' : 'Login required'}
            </button>

            <p className={styles.fineprint}>
              Secure payment via Razorpay · UPI, cards, netbanking & wallets
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

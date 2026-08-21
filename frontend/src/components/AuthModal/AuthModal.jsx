/**
 * Product Detective — Auth Modal
 * Login / Signup modal with detective-noir styling.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../hooks/useAuth'
import styles from './AuthModal.module.css'

export default function AuthModal({ open, onClose, mode: initialMode = 'login' }) {
  const { login, signup, loading, error, clearError } = useAuth()
  const [mode, setMode] = useState(initialMode)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (open) {
      setMode(initialMode)
      clearError()
    }
  }, [open, initialMode])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (mode === 'signup') {
        await signup(email, name, password)
      } else {
        await login(email, password)
      }
      onClose()
    } catch {
      /* error is in store */
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
              <span className="label">◈ {mode === 'signup' ? 'NEW RECRUIT' : 'ACCESS FILE'}</span>
              <button className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
            </div>

            <h2 className={styles.title}>
              {mode === 'signup' ? 'Join the Bureau' : 'Detective Login'}
            </h2>
            <p className={styles.subtitle}>
              {mode === 'signup'
                ? 'Create an account to save cases & unlock Pro.'
                : 'Welcome back, Detective.'}
            </p>

            <form onSubmit={handleSubmit} className={styles.form}>
              {mode === 'signup' && (
                <input
                  className={styles.input}
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  minLength={1}
                />
              )}
              <input
                className={styles.input}
                type="email"
                placeholder="email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <input
                className={styles.input}
                type="password"
                placeholder="Password (min 6 chars)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />

              {error && <div className={styles.error}>{error}</div>}

              <button
                type="submit"
                className="btn-primary"
                disabled={loading}
                style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              >
                {loading ? '...' : mode === 'signup' ? 'Create Account →' : 'Login →'}
              </button>
            </form>

            <div className={styles.switch}>
              {mode === 'signup' ? (
                <>Already have an account?{' '}
                  <button onClick={() => setMode('login')} className={styles.link}>Login</button>
                </>
              ) : (
                <>New here?{' '}
                  <button onClick={() => setMode('signup')} className={styles.link}>Sign up</button>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

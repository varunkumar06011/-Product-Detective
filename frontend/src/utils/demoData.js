/**
 * Product Detective — Demo Data
 * Pre-built investigation results used in demo mode.
 * Production: replaced by real API responses.
 */

export const DEMOS = {
  laptop: {
    id: 'laptop',
    label: 'Gaming Laptop',
    icon: '💻',
    url: 'https://demo.productdetective.ai/predator-helios-300',
    title: 'Predator Helios 300 Gaming Laptop (2024)',
    price: 89990,
    rating: 3.8,
    reviewCount: 1247,
    category: 'Gaming Laptop',
    verdict: 'WAIT',
    confidence: 71,
    evidence: [
      'Overheating complaints tripled in 6 months — likely hardware defect',
      'Cooling system scores 41/100 for a gaming-class laptop',
      'Review trust score 68/100 — possible manipulation spike in January',
      'GPU and CPU specs are competitive but thermal throttle under sustained load',
      'Better alternatives exist at same price with superior cooling',
    ],
    alternatives: [
      {
        rank: '01', name: 'ASUS ROG Strix G15 (2024)', price: 89990, score: 84,
        reasons: [
          'Vapor chamber cooling — only 12% overheating complaints',
          'RTX 4070 — stronger GPU at comparable price',
          'Stable review history with no defect spikes',
        ],
        why_better: 'Significantly better cooling + stronger GPU at same price',
        trust_score: 88, avg_rating: 4.3,
      },
      {
        rank: '02', name: 'Lenovo Legion 5 Pro (2024)', price: 92000, score: 88,
        reasons: [
          'Best-in-class thermals for gaming laptops',
          '90Wh battery — 50% more than competitors',
          'Trust score 91/100 — genuinely loved by owners',
        ],
        why_better: 'Best overall alternative — slight premium is worth it',
        trust_score: 91, avg_rating: 4.5,
      },
      {
        rank: '03', name: 'MSI Katana GF66', price: 69990, score: 72,
        reasons: [
          '₹20,000 cheaper alternative',
          'Consistent performance over 12 months',
          'Good price-to-GPU ratio',
        ],
        why_better: 'Budget-friendly with no major red flags',
        trust_score: 78, avg_rating: 4.1,
      },
    ],
    clueCards: [
      {
        id: 'sentiment', icon: '💬', title: 'Review Sentiment',
        stamp: 'warning', tag: 'MIXED SIGNALS',
        preview: '52% positive · 27% negative',
        detail: {
          label: 'SENTIMENT ANALYSIS — 1,247 REVIEWS',
          bars: [
            { label: 'Positive', pct: 52, type: 'good' },
            { label: 'Neutral',  pct: 21, type: 'warn' },
            { label: 'Negative', pct: 27, type: 'bad'  },
          ],
          tags: ['fast performance', 'good display', 'great value', 'overheating', 'poor battery', 'loud fan'],
          tagTypes: ['positive', 'positive', 'positive', 'complaint', 'complaint', 'complaint'],
          alert: { type: 'warning', text: '27% negative reviews is above the category average of 18%. Proceed with caution.' },
        },
      },
      {
        id: 'complaints', icon: '⚠️', title: 'Major Complaint Clue',
        stamp: 'danger', tag: 'RED FLAG',
        preview: 'Overheating in top complaints',
        detail: {
          label: 'TOP COMPLAINT CLUSTERS',
          bars: [
            { label: 'Overheating',  pct: 34, type: 'bad'  },
            { label: 'Battery life', pct: 28, type: 'bad'  },
            { label: 'Fan noise',    pct: 22, type: 'warn' },
            { label: 'Build quality',pct: 14, type: 'warn' },
            { label: 'Keyboard flex',pct: 9,  type: 'warn' },
          ],
          alert: { type: 'danger', text: 'Overheating reported by 34% of users — critical for a gaming laptop. Thermal throttling confirmed in 19 detailed reviews.' },
        },
      },
      {
        id: 'timeline', icon: '📈', title: 'Complaint Timeline',
        stamp: 'danger', tag: 'RISING TREND',
        preview: 'Overheating complaints tripling',
        detail: {
          label: 'COMPLAINT TREND — LAST 6 MONTHS',
          timeline: [
            { date: 'Oct 2024', text: 'Overheating complaints', pct: '8%',  type: 'stable' },
            { date: 'Nov 2024', text: 'Slight increase noted',   pct: '11%', type: 'stable' },
            { date: 'Dec 2024', text: 'Post-holiday spike',       pct: '16%', type: 'rise'   },
            { date: 'Jan 2025', text: 'User reports escalating',  pct: '22%', type: 'rise'   },
            { date: 'Feb 2025', text: 'Critical mass reached',    pct: '29%', type: 'rise'   },
            { date: 'Mar 2025', text: 'Current — still rising',   pct: '34%', type: 'rise'   },
          ],
          alert: { type: 'danger', text: 'Overheating complaints grew 325% in 6 months — strong signal of a hardware defect, not random user error.' },
        },
      },
      {
        id: 'trust', icon: '🛡️', title: 'Review Trust Score',
        stamp: 'warning', tag: 'SUSPICIOUS',
        preview: '68/100 — anomalies detected',
        detail: {
          label: 'REVIEW AUTHENTICITY ANALYSIS',
          score: { value: 68, type: 'warn', label: '/100' },
          bars: [
            { label: 'Verified purchases',      pct: 79, type: 'good' },
            { label: 'Duplicate review text',   pct: 12, type: 'warn' },
            { label: 'Rating vs text mismatch', pct: 9,  type: 'warn' },
            { label: 'Burst spike (Jan 2025)',  pct: 17, type: 'bad'  },
          ],
          alert: { type: 'warning', text: '17% of 5-star reviews were posted in a single week in January 2025 — unusual spike pattern detected.' },
        },
      },
      {
        id: 'specs', icon: '🔬', title: 'Spec Match Clue',
        stamp: 'warning', tag: 'COOLING WEAKNESS',
        preview: 'GPU adequate, cooling critical',
        detail: {
          label: 'GAMING LAPTOP SPEC EVALUATION',
          bars: [
            { label: 'GPU (RTX 3060)',    pct: 74, type: 'good' },
            { label: 'CPU (i7-12700H)',   pct: 82, type: 'good' },
            { label: 'Cooling System',    pct: 41, type: 'bad'  },
            { label: 'Battery (58Wh)',    pct: 38, type: 'bad'  },
            { label: 'Display (144Hz)',   pct: 85, type: 'good' },
            { label: 'RAM (16GB DDR5)',   pct: 78, type: 'good' },
          ],
          alert: { type: 'warning', text: 'Cooling system is the critical weak link — specs are strong but thermal design throttles sustained gaming performance.' },
        },
      },
    ],
  },

  phone: {
    id: 'phone',
    label: 'Smartphone',
    icon: '📱',
    url: 'https://demo.productdetective.ai/galaxy-a54',
    title: 'Samsung Galaxy A54 5G (128GB)',
    price: 32999,
    rating: 4.2,
    reviewCount: 3891,
    category: 'Smartphone',
    verdict: 'BUY',
    confidence: 84,
    evidence: [
      '74% positive reviews — best-in-class sentiment for mid-range Android',
      'Complaint trends completely stable — no hidden defects emerging',
      'Review trust score 89/100 — genuinely authentic user opinions',
      '4 years of guaranteed OS updates — exceptional for mid-range',
      'Only notable weakness is 25W charging — a design choice, not a defect',
    ],
    alternatives: [],
    clueCards: [
      {
        id: 'sentiment', icon: '💬', title: 'Review Sentiment',
        stamp: 'safe', tag: 'STRONGLY POSITIVE',
        preview: '74% positive · 10% negative',
        detail: {
          label: 'SENTIMENT ANALYSIS — 3,891 REVIEWS',
          bars: [
            { label: 'Positive', pct: 74, type: 'good' },
            { label: 'Neutral',  pct: 16, type: 'warn' },
            { label: 'Negative', pct: 10, type: 'bad'  },
          ],
          tags: ['great camera', 'smooth UI', 'good battery', 'long updates', 'solid build'],
          tagTypes: ['positive', 'positive', 'positive', 'positive', 'positive'],
          alert: { type: 'success', text: 'Best-in-class sentiment for mid-range Android. 10% negative is well below the 18% category average.' },
        },
      },
      {
        id: 'complaints', icon: '⚠️', title: 'Major Complaints',
        stamp: 'warning', tag: 'MINOR ISSUES ONLY',
        preview: 'Design choices, not defects',
        detail: {
          label: 'TOP COMPLAINT CLUSTERS',
          bars: [
            { label: 'Slow charging (25W)',        pct: 18, type: 'warn' },
            { label: 'No 3.5mm headphone jack',    pct: 14, type: 'warn' },
            { label: 'Plastic back panel',         pct: 11, type: 'warn' },
            { label: 'No expandable storage',      pct: 8,  type: 'warn' },
          ],
          alert: { type: 'warning', text: 'Complaints are design trade-offs, not defects. Slow charging is the most common frustration but not a reliability issue.' },
        },
      },
      {
        id: 'timeline', icon: '📈', title: 'Complaint Timeline',
        stamp: 'safe', tag: 'COMPLETELY STABLE',
        preview: 'No emerging complaint trends',
        detail: {
          label: 'COMPLAINT TREND — 6 MONTHS',
          timeline: [
            { date: 'Oct 2024', text: 'Charging complaints', pct: '16%', type: 'stable' },
            { date: 'Dec 2024', text: 'Consistent pattern',  pct: '17%', type: 'stable' },
            { date: 'Feb 2025', text: 'No new issues',       pct: '18%', type: 'stable' },
          ],
          alert: { type: 'success', text: 'Completely stable complaint pattern — a mature, well-understood product with no hidden defects emerging.' },
        },
      },
      {
        id: 'trust', icon: '🛡️', title: 'Review Trust Score',
        stamp: 'safe', tag: 'HIGHLY AUTHENTIC',
        preview: '89/100 — A grade',
        detail: {
          label: 'AUTHENTICITY ANALYSIS',
          score: { value: 89, type: 'safe', label: '/100' },
          bars: [
            { label: 'Verified purchases',   pct: 94, type: 'good' },
            { label: 'Duplicate content',    pct: 2,  type: 'good' },
            { label: 'Spike anomalies',      pct: 0,  type: 'good' },
            { label: 'Rating-text mismatch', pct: 4,  type: 'good' },
          ],
          alert: { type: 'success', text: 'Excellent review authenticity. No manipulation patterns detected across 3,891 reviews spanning 14 months.' },
        },
      },
      {
        id: 'specs', icon: '🔬', title: 'Spec Match Clue',
        stamp: 'safe', tag: 'STRONG ALL-ROUNDER',
        preview: 'Well-balanced mid-range package',
        detail: {
          label: 'SMARTPHONE SPEC EVALUATION',
          bars: [
            { label: 'Camera (50MP OIS)',         pct: 83, type: 'good' },
            { label: 'Processor (Exynos 1380)',   pct: 71, type: 'good' },
            { label: 'Battery (5000mAh)',         pct: 88, type: 'good' },
            { label: 'Charging speed (25W)',      pct: 52, type: 'warn' },
            { label: 'Display (Super AMOLED)',    pct: 91, type: 'good' },
          ],
          alert: { type: 'success', text: 'Strong all-rounder. 4 years of OS updates is exceptional for mid-range — adds significant long-term value.' },
        },
      },
    ],
  },

  earbuds: {
    id: 'earbuds',
    label: 'Earbuds',
    icon: '🎧',
    url: 'https://demo.productdetective.ai/boat-airdopes-141',
    title: 'boAt Airdopes 141 TWS Earbuds',
    price: 1299,
    rating: 3.6,
    reviewCount: 28432,
    category: 'Wireless Earbuds',
    verdict: 'AVOID',
    confidence: 88,
    evidence: [
      '41% negative reviews — nearly double the 22% category average',
      '"One earbud stops working" defect affects 31% of users — manufacturing issue',
      'Complaint trends accelerating with no response from manufacturer',
      'Trust score 54/100 — significant review manipulation detected',
      'Better alternatives available at identical price with proven reliability',
    ],
    alternatives: [
      {
        rank: '01', name: 'Noise Buds VS104', price: 1499, score: 77,
        reasons: [
          'Same price bracket as reviewed product',
          'Only 11% negative reviews vs 41%',
          'Stable quality for 8+ months',
        ],
        why_better: 'Reliable alternative at essentially the same price',
        trust_score: 82, avg_rating: 4.1,
      },
      {
        rank: '02', name: 'Realme Buds T100', price: 1499, score: 75,
        reasons: [
          'Far better durability track record',
          'Trust score 82/100',
          'Consistently good mic quality reported',
        ],
        why_better: 'More trustworthy reviews + better reliability',
        trust_score: 82, avg_rating: 4.0,
      },
    ],
    clueCards: [
      {
        id: 'sentiment', icon: '💬', title: 'Review Sentiment',
        stamp: 'danger', tag: 'NEGATIVE LEAN',
        preview: '43% positive · 41% negative',
        detail: {
          label: 'SENTIMENT ANALYSIS — 28,432 REVIEWS',
          bars: [
            { label: 'Positive', pct: 43, type: 'good' },
            { label: 'Neutral',  pct: 16, type: 'warn' },
            { label: 'Negative', pct: 41, type: 'bad'  },
          ],
          tags: ['good bass', 'looks good', 'connectivity drops', 'poor durability', 'stops working'],
          tagTypes: ['positive', 'positive', 'complaint', 'complaint', 'complaint'],
          alert: { type: 'danger', text: '41% negative — nearly double the earbuds category average of 22%. High volume (28k reviews) makes this highly statistically significant.' },
        },
      },
      {
        id: 'complaints', icon: '⚠️', title: 'Major Complaints',
        stamp: 'danger', tag: 'CRITICAL DEFECTS',
        preview: 'Connectivity & hardware failures',
        detail: {
          label: 'TOP COMPLAINT CLUSTERS',
          bars: [
            { label: 'Connectivity drops',    pct: 38, type: 'bad'  },
            { label: 'One earbud dies',       pct: 31, type: 'bad'  },
            { label: 'Poor mic quality',      pct: 27, type: 'bad'  },
            { label: 'Uncomfortable fit',     pct: 24, type: 'warn' },
            { label: 'Charging case issues',  pct: 18, type: 'warn' },
          ],
          alert: { type: 'danger', text: '"One earbud stops working" at 31% — this is a manufacturing defect pattern, not random user error. Batch quality control has failed.' },
        },
      },
      {
        id: 'timeline', icon: '📈', title: 'Complaint Timeline',
        stamp: 'danger', tag: 'ACCELERATING',
        preview: 'Defects doubling every quarter',
        detail: {
          label: 'COMPLAINT TREND — 6 MONTHS',
          timeline: [
            { date: 'Sep 2024', text: 'Connectivity drops',           pct: '22%', type: 'stable' },
            { date: 'Nov 2024', text: 'One earbud failures spike',    pct: '28%', type: 'rise'   },
            { date: 'Jan 2025', text: 'Defect reports escalating',    pct: '35%', type: 'rise'   },
            { date: 'Mar 2025', text: 'No improvement from brand',    pct: '41%', type: 'rise'   },
          ],
          alert: { type: 'danger', text: 'Complaints nearly doubled in 6 months with zero response from the manufacturer — strong and unambiguous AVOID signal.' },
        },
      },
      {
        id: 'trust', icon: '🛡️', title: 'Review Trust Score',
        stamp: 'danger', tag: 'LOW TRUST',
        preview: '54/100 — manipulation likely',
        detail: {
          label: 'AUTHENTICITY ANALYSIS',
          score: { value: 54, type: 'bad', label: '/100' },
          bars: [
            { label: 'Verified purchases',   pct: 61, type: 'warn' },
            { label: 'Generic 5-star text',  pct: 31, type: 'bad'  },
            { label: 'Rating-text mismatch', pct: 24, type: 'bad'  },
            { label: 'Burst spike detected', pct: 28, type: 'bad'  },
          ],
          alert: { type: 'danger', text: 'Significant review manipulation. True rating estimated at 3.1★ after filtering suspicious reviews. Actual product is worse than ratings suggest.' },
        },
      },
      {
        id: 'specs', icon: '🔬', title: 'Spec Match Clue',
        stamp: 'warning', tag: 'MISLEADING SPECS',
        preview: 'Specs look fine, reality differs',
        detail: {
          label: 'SPEC VS REAL-WORLD CHECK',
          bars: [
            { label: 'Battery (claimed 42hr)', pct: 65, type: 'warn' },
            { label: 'Bluetooth 5.0',          pct: 58, type: 'warn' },
            { label: 'IPX4 rating',            pct: 50, type: 'warn' },
            { label: 'Driver quality (6mm)',   pct: 42, type: 'bad'  },
          ],
          alert: { type: 'danger', text: 'Real-world performance is significantly below claimed specs based on 847 detailed reviews with specific measurements.' },
        },
      },
    ],
  },
}

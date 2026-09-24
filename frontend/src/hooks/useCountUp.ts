import { useState, useEffect } from 'react'

/**
 * Cubic-bezier evaluator — matches CSS cubic-bezier(0.16, 1, 0.3, 1).
 * All hero animations in APEX LINK use this same curve.
 */
function cubicBezier(t: number): number {
  // Approximation of cubic-bezier(0.16, 1, 0.3, 1)
  // Fast start, decelerating landing — the "ease-out-cubic" motion signature.
  const p = 1 - t
  return 1 - (p * p * p * 0.84 + 3 * p * p * t * 0.3 + 3 * p * t * t * 1.0)
}

/**
 * Animates a number from 0 → target over `duration` ms.
 * Uses requestAnimationFrame for GPU-smooth interpolation.
 * Respects prefers-reduced-motion (returns target immediately).
 */
export function useCountUp(target: number, duration = 800): number {
  const [value, setValue] = useState(0)
  const reducedMotion = typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (reducedMotion || target === 0) {
      setValue(target)
      return
    }

    let raf: number
    const start = performance.now()

    const tick = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = cubicBezier(progress)
      setValue(Math.round(eased * target))
      if (progress < 1) {
        raf = requestAnimationFrame(tick)
      }
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, reducedMotion])

  return value
}

import { useState, useEffect } from 'react'

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
      // ease-out cubic — fast start, soft landing
      const eased = 1 - Math.pow(1 - progress, 3)
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

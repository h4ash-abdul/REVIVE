import React from 'react'
import { cn } from '../../lib/utils'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("bg-panel border border-borderRef rounded-[3px]", className)} {...props} />
  )
)
Card.displayName = "Card"

export const Badge = ({ className, variant = 'low', ...props }: React.HTMLAttributes<HTMLSpanElement> & { variant?: 'critical' | 'elevated' | 'low' | 'success' }) => {
  const variants = {
    critical: "bg-criticalBg text-critical",
    elevated: "bg-elevatedBg text-elevated",
    low: "bg-lowBg text-textSecondary",
    success: "bg-successBg text-success"
  }
  return (
    <span className={cn("px-2.5 py-1 rounded-[2px] text-[10px] font-semibold tracking-[0.4px] uppercase", variants[variant], className)} {...props} />
  )
}

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'outline' }>(
  ({ className, variant = 'outline', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-[3px] text-xs font-medium cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed",
          variant === 'primary' ? "bg-dark text-white border border-dark hover:brightness-95" : "bg-panel text-textPrimary border border-borderStrong hover:bg-panelAlt",
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

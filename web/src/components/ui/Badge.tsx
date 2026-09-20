import React from 'react';
import { cn } from '../../utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'danger' | 'neutral';
}

export function Badge({ className, variant = 'neutral', children, ...props }: BadgeProps) {
  const variants = {
    success: 'bg-[#216B45]/10 text-[--success]',
    warning: 'bg-[#865507]/10 text-[--warning]',
    danger: 'bg-[--danger]/10 text-[--danger]',
    neutral: 'bg-[--surface-soft] text-[--muted]'
  };

  return (
    <span className={cn("inline-flex items-center px-2 py-1 rounded-full label font-medium", variants[variant], className)} {...props}>
      {children}
    </span>
  );
}

import React from 'react';
import { cn } from '../../utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'tertiary';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', isLoading, children, disabled, ...props }, ref) => {
    const base = "inline-flex items-center justify-center font-body font-medium rounded-[10px] min-h-[48px] px-[18px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--focus] focus-visible:ring-offset-3 disabled:opacity-50 disabled:pointer-events-none";
    const variants = {
      primary: "bg-[--primary] text-white hover:bg-[--primary-hover]",
      secondary: "bg-transparent text-[--ink] border border-[--ink] hover:bg-[--surface-soft]",
      tertiary: "bg-transparent text-[--primary] hover:bg-[--primary-soft] underline-offset-4 hover:underline"
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? <span className="mr-2 animate-spin border-2 border-current border-t-transparent rounded-full w-4 h-4" /> : null}
        {children}
      </button>
    );
  }
);

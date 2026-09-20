import React from 'react';
import { cn } from '../../utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helpText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helpText, id, ...props }, ref) => {
    const inputId = id || React.useId();
    return (
      <div className="flex flex-col gap-[--space-8]">
        <label htmlFor={inputId} className="label font-medium text-[--ink]">{label}</label>
        {helpText && <span className="metadata text-[--muted]">{helpText}</span>}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            "flex h-[48px] w-full rounded-[10px] border border-[--border] bg-[--surface] px-[--space-16] py-2 text-base placeholder:text-[--muted] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--focus] focus-visible:ring-offset-3 disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-[--danger] focus-visible:ring-[--danger]",
            className
          )}
          {...props}
        />
        {error && <span className="metadata text-[--danger]">{error}</span>}
      </div>
    );
  }
);

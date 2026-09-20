import React from 'react';
import { cn } from '../../utils';

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("bg-[--surface] rounded-[16px] shadow-default p-[--space-24] md:p-[--space-20] lg:p-[--space-24]", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("mb-[--space-16] flex flex-col gap-[--space-4]", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn("h3 font-headings font-bold text-[--ink]", className)} {...props}>
      {children}
    </h3>
  );
}

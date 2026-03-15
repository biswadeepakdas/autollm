import { clsx } from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      className={clsx("bg-white rounded-2xl border border-gray-100 shadow-sm", className)}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

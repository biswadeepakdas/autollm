export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={`w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin ${className}`} />
  );
}

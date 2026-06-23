export function LoadingState() {
  return <div className="status">Loading data...</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="status error">{message}</div>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="status">{message}</div>;
}


function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12" role="status" aria-label="Loading">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-teal-200 border-t-teal-600" />
    </div>
  );
}

export default LoadingSpinner;

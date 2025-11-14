/**
 * Reusable Loading Spinner Component
 */

function LoadingSpinner({ size = 'md', message = null }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  const spinnerSize = sizeClasses[size] || sizeClasses.md

  return (
    <div className="flex items-center justify-center">
      <div className={`inline-block animate-spin rounded-full border-b-2 border-blue-600 ${spinnerSize}`}></div>
      {message && <p className="text-gray-500 ml-4">{message}</p>}
    </div>
  )
}

export default LoadingSpinner

/**
 * Reusable Error Alert Component
 */

function ErrorAlert({ message, onDismiss = null }) {
  if (!message) return null

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <span className="text-red-600 mr-2">⚠️</span>
          <p className="text-red-800 text-sm font-medium">{message}</p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-600 hover:text-red-800"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}

export default ErrorAlert

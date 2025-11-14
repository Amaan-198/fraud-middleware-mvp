/**
 * Reusable Badge Component
 *
 * Displays status badges with consistent styling
 */

const BADGE_STYLES = {
  success: 'bg-green-100 text-green-800 border-green-300',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  error: 'bg-red-100 text-red-800 border-red-300',
  info: 'bg-blue-100 text-blue-800 border-blue-300',
  neutral: 'bg-gray-100 text-gray-800 border-gray-300',
}

function Badge({ variant = 'neutral', children, className = '' }) {
  const baseStyle = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border'
  const variantStyle = BADGE_STYLES[variant] || BADGE_STYLES.neutral

  return (
    <span className={`${baseStyle} ${variantStyle} ${className}`}>
      {children}
    </span>
  )
}

export default Badge

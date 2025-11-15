import { Card } from './common'

function SessionCard({ session, onClick }) {
  // Calculate risk level and color
  const getRiskLevel = (score) => {
    if (score >= 80) return { level: 'CRITICAL', color: 'red', bg: 'bg-red-50', border: 'border-red-500' }
    if (score >= 60) return { level: 'HIGH', color: 'orange', bg: 'bg-orange-50', border: 'border-orange-500' }
    if (score >= 30) return { level: 'ELEVATED', color: 'yellow', bg: 'bg-yellow-50', border: 'border-yellow-500' }
    return { level: 'SAFE', color: 'green', bg: 'bg-green-50', border: 'border-green-500' }
  }

  const risk = getRiskLevel(session.risk_score)

  // Get status badge
  const getStatusBadge = () => {
    if (session.is_terminated) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800">
          🚫 TERMINATED
        </span>
      )
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-800">
        <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5 animate-pulse"></span>
        ACTIVE
      </span>
    )
  }

  // Format anomalies for display
  const getAnomalySummary = () => {
    const anomalies = session.anomalies || []
    if (anomalies.length === 0) return 'No anomalies detected'
    if (anomalies.length === 1) return anomalies[0].split(':')[0].replace(/_/g, ' ')
    return `${anomalies.length} anomalies detected`
  }

  return (
    <Card 
      className={`cursor-pointer transition-all duration-200 hover:shadow-xl hover:scale-[1.02] border-l-4 ${risk.border} ${risk.bg}`}
      onClick={onClick}
    >
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-mono text-gray-700 truncate">
                {session.session_id}
              </h3>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Account: <span className="font-semibold">{session.account_id}</span>
            </p>
          </div>
          {getStatusBadge()}
        </div>

        {/* Risk Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">Risk Score</span>
            <span className={`text-lg font-bold text-${risk.color}-600`}>
              {session.risk_score.toFixed(1)}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 bg-${risk.color}-500`}
              style={{ width: `${Math.min(session.risk_score, 100)}%` }}
            ></div>
          </div>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold text-${risk.color}-700`}>
              {risk.level}
            </span>
            <span className="text-xs text-gray-500">
              {session.risk_score >= 80 && '⚠️ Auto-terminated'}
            </span>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-200">
          <div>
            <p className="text-xs text-gray-500">Transactions</p>
            <p className="text-lg font-bold text-gray-900">{session.transaction_count}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Total Amount</p>
            <p className="text-lg font-bold text-gray-900">
              ₹{session.total_amount?.toLocaleString() || '0'}
            </p>
          </div>
        </div>

        {/* Anomalies */}
        <div className="pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Anomalies</p>
          <p className="text-xs text-gray-700 font-medium">
            {getAnomalySummary()}
          </p>
        </div>

        {/* Click hint */}
        <div className="pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-400 text-center">
            Click for details →
          </p>
        </div>
      </div>
    </Card>
  )
}

export default SessionCard

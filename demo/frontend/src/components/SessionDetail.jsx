import { useState } from 'react'
import { Card, LoadingSpinner, ErrorAlert } from './common'
import api from '../services/api'

function SessionDetail({ session, onClose, onUpdate }) {
  const [terminating, setTerminating] = useState(false)
  const [error, setError] = useState(null)

  // Calculate risk level
  const getRiskLevel = (score) => {
    if (score >= 80) return { level: 'CRITICAL', color: 'text-red-600', bg: 'bg-red-50' }
    if (score >= 60) return { level: 'HIGH', color: 'text-orange-600', bg: 'bg-orange-50' }
    if (score >= 30) return { level: 'ELEVATED', color: 'text-yellow-600', bg: 'bg-yellow-50' }
    return { level: 'SAFE', color: 'text-green-600', bg: 'bg-green-50' }
  }

  const risk = getRiskLevel(session.risk_score)

  // Handle terminate
  const handleTerminate = async () => {
    if (!confirm('Are you sure you want to terminate this session?')) {
      return
    }

    try {
      setTerminating(true)
      setError(null)
      await api.terminateSession(session.session_id, 'Manual termination by analyst')
      if (onUpdate) {
        onUpdate()
      }
    } catch (err) {
      setError(err.message || 'Failed to terminate session')
    } finally {
      setTerminating(false)
    }
  }

  // Parse anomalies
  const parseAnomaly = (anomaly) => {
    const parts = anomaly.split(':')
    if (parts.length >= 2) {
      return {
        type: parts[0].replace(/_/g, ' '),
        details: parts.slice(1).join(':')
      }
    }
    return { type: anomaly, details: '' }
  }

  const anomalies = session.anomalies || []

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className={`${risk.bg} border-b border-gray-200 px-6 py-4`}>
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Session Details</h2>
              <p className="text-sm text-gray-600 mt-1 font-mono">{session.session_id}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && <ErrorAlert message={error} />}

          {/* Status and Risk */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <div className="text-center">
                <p className="text-sm text-gray-500 mb-2">Status</p>
                {session.is_terminated ? (
                  <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-bold bg-red-100 text-red-800">
                    🚫 TERMINATED
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-bold bg-green-100 text-green-800">
                    <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                    ACTIVE
                  </span>
                )}
              </div>
            </Card>

            <Card>
              <div className="text-center">
                <p className="text-sm text-gray-500 mb-2">Risk Level</p>
                <p className={`text-2xl font-bold ${risk.color}`}>{risk.level}</p>
              </div>
            </Card>

            <Card>
              <div className="text-center">
                <p className="text-sm text-gray-500 mb-2">Risk Score</p>
                <p className={`text-3xl font-bold ${risk.color}`}>
                  {session.risk_score.toFixed(1)}
                </p>
              </div>
            </Card>
          </div>

          {/* Account & Metrics */}
          <Card>
            <h3 className="text-lg font-semibold mb-4">Session Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Account ID</p>
                <p className="text-sm font-semibold text-gray-900">{session.account_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Transactions</p>
                <p className="text-sm font-semibold text-gray-900">{session.transaction_count}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Total Amount</p>
                <p className="text-sm font-semibold text-gray-900">
                  ₹{session.total_amount?.toLocaleString() || '0'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Created At</p>
                <p className="text-sm font-semibold text-gray-900">
                  {session.created_at ? new Date(session.created_at).toLocaleTimeString() : 'N/A'}
                </p>
              </div>
            </div>
          </Card>

          {/* Anomalies */}
          <Card>
            <h3 className="text-lg font-semibold mb-4">
              Detected Anomalies ({anomalies.length})
            </h3>
            {anomalies.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-6xl mb-2">✅</div>
                <p className="text-gray-500">No anomalies detected</p>
                <p className="text-xs text-gray-400 mt-1">This session shows normal behavior patterns</p>
              </div>
            ) : (
              <div className="space-y-3">
                {anomalies.map((anomaly, idx) => {
                  const parsed = parseAnomaly(anomaly)
                  return (
                    <div key={idx} className="flex items-start space-x-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <div className="flex-shrink-0">
                        <span className="text-xl">⚠️</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-red-900 capitalize">
                          {parsed.type}
                        </p>
                        <p className="text-xs text-red-700 mt-1">
                          {parsed.details}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          {/* Behavioral Signals */}
          {session.signals_triggered && session.signals_triggered.length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold mb-4">
                Triggered Signals ({session.signals_triggered.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {session.signals_triggered.map((signal, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800"
                  >
                    {signal.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </Card>
          )}

          {/* Termination Info */}
          {session.is_terminated && session.termination_reason && (
            <Card>
              <h3 className="text-lg font-semibold mb-4 text-red-700">Termination Information</h3>
              <div className="space-y-2">
                <div>
                  <p className="text-xs text-gray-500">Reason</p>
                  <p className="text-sm text-gray-900">{session.termination_reason}</p>
                </div>
                {session.terminated_at && (
                  <div>
                    <p className="text-xs text-gray-500">Terminated At</p>
                    <p className="text-sm text-gray-900">
                      {new Date(session.terminated_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Last updated: {new Date(session.updated_at || session.created_at).toLocaleString()}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
              {!session.is_terminated && (
                <button
                  onClick={handleTerminate}
                  disabled={terminating}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {terminating ? (
                    <>
                      <LoadingSpinner size="small" />
                      <span>Terminating...</span>
                    </>
                  ) : (
                    <>
                      <span>🚫</span>
                      <span>Terminate Session</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SessionDetail

import { useState, useEffect } from 'react'
import { ENDPOINTS } from '../config'

function AuditTrail() {
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const fetchAuditTrail = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(ENDPOINTS.auditTrail)
      if (!response.ok) {
        throw new Error(`Failed to fetch audit trail: ${response.status}`)
      }

      const data = await response.json()
      setAuditLogs(data)
    } catch (err) {
      setError(err.message)
      // Don't clear existing data on error - graceful degradation
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAuditTrail()
  }, [])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchAuditTrail, 10000) // Refresh every 10 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const getActionBadge = (action) => {
    const badges = {
      'review_event': { class: 'bg-blue-100 text-blue-800', icon: '👁️' },
      'unblock_source': { class: 'bg-green-100 text-green-800', icon: '✅' },
      'set_rate_limit': { class: 'bg-yellow-100 text-yellow-800', icon: '⏱️' },
      'block_source': { class: 'bg-red-100 text-red-800', icon: '🚫' },
      'decision_request': { class: 'bg-purple-100 text-purple-800', icon: '🔍' },
      'data_access': { class: 'bg-indigo-100 text-indigo-800', icon: '📊' },
      'default': { class: 'bg-gray-100 text-gray-800', icon: '📝' }
    }

    const badge = badges[action] || badges['default']
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${badge.class} inline-flex items-center space-x-1`}>
        <span>{badge.icon}</span>
        <span>{action.replace(/_/g, ' ').toUpperCase()}</span>
      </span>
    )
  }

  const getSuccessBadge = (success) => {
    return success ? (
      <span className="px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
        ✓ Success
      </span>
    ) : (
      <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">
        ✗ Failed
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">📋 Audit Trail</h2>
            <p className="text-sm text-gray-600 mt-1">
              Complete audit log of all security and fraud operations
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700">Auto-refresh (10s)</span>
            </label>
            <button
              onClick={fetchAuditTrail}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm font-medium">⚠️ {error}</p>
          <p className="text-red-600 text-xs mt-1">
            Showing last successful data. Click Refresh to try again.
          </p>
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Logs</p>
              <p className="text-2xl font-bold text-gray-900">{auditLogs.length}</p>
            </div>
            <div className="text-3xl">📊</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Successful</p>
              <p className="text-2xl font-bold text-green-600">
                {auditLogs.filter(log => log.success).length}
              </p>
            </div>
            <div className="text-3xl">✅</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-2xl font-bold text-red-600">
                {auditLogs.filter(log => !log.success).length}
              </p>
            </div>
            <div className="text-3xl">❌</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unique Sources</p>
              <p className="text-2xl font-bold text-blue-600">
                {new Set(auditLogs.map(log => log.source_id)).size}
              </p>
            </div>
            <div className="text-3xl">👤</div>
          </div>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        {loading && auditLogs.length === 0 ? (
          <div className="p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="text-gray-600 mt-4">Loading audit trail...</p>
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">No audit logs available</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Resource
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Metadata
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {auditLogs.map((log, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        {new Date(log.timestamp).toLocaleDateString()}
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {log.source_id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getActionBadge(log.action)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                      {log.resource || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getSuccessBadge(log.success)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {log.metadata && Object.keys(log.metadata).length > 0 ? (
                        <details className="cursor-pointer">
                          <summary className="text-blue-600 hover:text-blue-800">
                            View metadata
                          </summary>
                          <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono">
                            {JSON.stringify(log.metadata, null, 2)}
                          </div>
                        </details>
                      ) : (
                        <span className="text-gray-400">No metadata</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Activity Timeline - Recent 10 logs */}
      {auditLogs.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Recent Activity Timeline</h3>
          <div className="space-y-3">
            {auditLogs.slice(0, 10).map((log, index) => (
              <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900">
                      {log.source_id} - {log.action.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    Resource: {log.resource || 'N/A'} • Status: {log.success ? 'Success' : 'Failed'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AuditTrail

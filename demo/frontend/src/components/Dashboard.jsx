import { useState, useEffect, useRef } from 'react'
import { ENDPOINTS } from '../config'

function Dashboard() {
  const [securityStats, setSecurityStats] = useState(null)
  const [decisionHealth, setDecisionHealth] = useState(null)
  const [securityHealth, setSecurityHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const errorCountRef = useRef(0)
  const retryTimeoutRef = useRef(null)

  useEffect(() => {
    fetchDashboardData()
    // Refresh every 10 seconds
    const interval = setInterval(fetchDashboardData, 10000)
    return () => {
      clearInterval(interval)
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
      }
    }
  }, [])

  const fetchWithTimeout = async (url, timeout = 5000) => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      return await response.json()
    } catch (err) {
      clearTimeout(timeoutId)
      throw err
    }
  }

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch endpoints individually to prevent one failure from breaking all
      const results = await Promise.allSettled([
        fetchWithTimeout(ENDPOINTS.securityDashboard),
        fetchWithTimeout(ENDPOINTS.decisionHealth),
        fetchWithTimeout(ENDPOINTS.securityHealth),
      ])

      // Update only successful fetches - graceful degradation
      if (results[0].status === 'fulfilled') {
        setSecurityStats(results[0].value)
        errorCountRef.current = 0 // Reset error count on success
      }
      if (results[1].status === 'fulfilled') {
        setDecisionHealth(results[1].value)
      }
      if (results[2].status === 'fulfilled') {
        setSecurityHealth(results[2].value)
      }

      // Check if all failed
      const allFailed = results.every(r => r.status === 'rejected')
      if (allFailed) {
        errorCountRef.current++
        const errors = results.map(r => r.reason?.message || 'Unknown error').join(', ')
        setError(`Failed to fetch data: ${errors}`)

        // If multiple consecutive failures, show more prominent error
        if (errorCountRef.current >= 3) {
          setError(`Network issues detected. Retrying... (${errorCountRef.current} consecutive failures)`)
        }
      } else {
        // At least some succeeded
        errorCountRef.current = 0
        setLastUpdate(new Date())
      }
    } catch (err) {
      errorCountRef.current++
      setError(`Error: ${err.message}`)
      // Don't clear existing data on error - graceful degradation
    } finally {
      setLoading(false)
    }
  }

  if (loading && !securityStats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="text-gray-500 ml-4">Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Error Banner - non-blocking */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-yellow-600 mr-2">⚠️</span>
              <div>
                <p className="text-yellow-800 text-sm font-medium">{error}</p>
                <p className="text-yellow-600 text-xs mt-1">
                  Showing last successful data. The system will continue trying to refresh.
                </p>
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-yellow-600 hover:text-yellow-800"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* System Health */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">System Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Decision Pipeline</p>
                <p className="text-2xl font-bold text-green-600">
                  {decisionHealth?.status || 'Unknown'}
                </p>
              </div>
              <div className="text-4xl">
                {decisionHealth?.status === 'healthy' ? '✓' : '⚠️'}
              </div>
            </div>
            {decisionHealth?.engines && (
              <div className="mt-3 text-xs text-gray-600">
                <div>Rules: {decisionHealth.engines.rules}</div>
                <div>ML: {decisionHealth.engines.ml}</div>
                <div>Policy: {decisionHealth.engines.policy}</div>
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Security Subsystem</p>
                <p className="text-2xl font-bold text-green-600">
                  {securityHealth?.status || 'Unknown'}
                </p>
              </div>
              <div className="text-4xl">
                {securityHealth?.status === 'healthy' ? '🛡️' : '⚠️'}
              </div>
            </div>
            {securityHealth?.metrics && (
              <div className="mt-3 text-xs text-gray-600">
                <div>Monitored Sources: {securityHealth.metrics.monitored_sources}</div>
                <div>Active Limits: {securityHealth.metrics.active_rate_limits}</div>
                <div>Total Events: {securityHealth.metrics.total_events}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Events"
          value={securityStats?.total_events || 0}
          icon="📋"
          color="blue"
        />
        <MetricCard
          title="Pending Reviews"
          value={securityStats?.pending_reviews || 0}
          icon="⏳"
          color="yellow"
        />
        <MetricCard
          title="Blocked Sources"
          value={securityStats?.blocked_sources || 0}
          icon="🚫"
          color="red"
        />
        <MetricCard
          title="Active Monitoring"
          value={securityHealth?.metrics?.monitored_sources || 0}
          icon="👁️"
          color="green"
        />
      </div>

      {/* Threat Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Threat Level Distribution</h3>
          {securityStats?.threat_level_distribution ? (
            <div className="space-y-3">
              {Object.entries(securityStats.threat_level_distribution).map(([level, count]) => (
                <div key={level} className="flex items-center">
                  <div className="w-24 text-sm text-gray-600">Level {level}</div>
                  <div className="flex-1">
                    <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div
                        className={`h-full ${getThreatLevelColor(parseInt(level))}`}
                        style={{
                          width: `${Math.min(
                            100,
                            (count / Math.max(...Object.values(securityStats.threat_level_distribution))) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm font-medium text-gray-900">{count}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No data available</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Threat Type Distribution</h3>
          {securityStats?.threat_type_distribution ? (
            <div className="space-y-3">
              {Object.entries(securityStats.threat_type_distribution).map(([type, count]) => (
                <div key={type} className="flex items-center">
                  <div className="w-32 text-sm text-gray-600 truncate">{type}</div>
                  <div className="flex-1">
                    <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div
                        className="h-full bg-purple-500"
                        style={{
                          width: `${Math.min(
                            100,
                            (count / Math.max(...Object.values(securityStats.threat_type_distribution))) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm font-medium text-gray-900">{count}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No data available</p>
          )}
        </div>
      </div>

      {/* Recent Events */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent High-Priority Events</h3>
        {securityStats?.recent_events && securityStats.recent_events.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Level</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {securityStats.recent_events.slice(0, 10).map((event, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-900">{event.threat_type}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getThreatLevelBadge(event.threat_level)}`}>
                        Level {event.threat_level}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 font-mono">{event.source_identifier}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{event.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No recent high-priority events</p>
        )}
      </div>

      {/* Refresh Info */}
      <div className="text-center text-sm text-gray-500">
        <span className="inline-flex items-center">
          <span className={`w-2 h-2 rounded-full mr-2 ${error ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`}></span>
          Auto-refreshing every 10 seconds
          {lastUpdate && ` • Last updated: ${lastUpdate.toLocaleTimeString()}`}
        </span>
      </div>
    </div>
  )
}

function MetricCard({ title, value, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    green: 'bg-green-50 text-green-600',
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`text-4xl p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function getThreatLevelColor(level) {
  const colors = {
    0: 'bg-gray-400',
    1: 'bg-blue-400',
    2: 'bg-yellow-400',
    3: 'bg-orange-500',
    4: 'bg-red-600',
  }
  return colors[level] || 'bg-gray-400'
}

function getThreatLevelBadge(level) {
  const badges = {
    0: 'bg-gray-100 text-gray-800',
    1: 'bg-blue-100 text-blue-800',
    2: 'bg-yellow-100 text-yellow-800',
    3: 'bg-orange-100 text-orange-800',
    4: 'bg-red-100 text-red-800',
  }
  return badges[level] || 'bg-gray-100 text-gray-800'
}

export default Dashboard

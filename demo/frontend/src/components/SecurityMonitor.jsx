import { useState, useEffect, useRef } from 'react'
import { ENDPOINTS } from '../config'

function SecurityMonitor() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [filters, setFilters] = useState({
    limit: 50,
    min_threat_level: 0,
    threat_type: '',
    source_id: '',
  })
  const [autoRefresh, setAutoRefresh] = useState(false)
  const errorCountRef = useRef(0)

  useEffect(() => {
    fetchEvents()
  }, [filters])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchEvents, 5000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, filters])

  const fetchEvents = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      params.append('limit', filters.limit)
      params.append('min_threat_level', filters.min_threat_level)
      if (filters.threat_type) params.append('threat_type', filters.threat_type)
      if (filters.source_id) params.append('source_id', filters.source_id)

      // Add timeout to fetch
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)

      const response = await fetch(`${ENDPOINTS.securityEvents}?${params}`, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setEvents(data)
      setLastUpdate(new Date())
      errorCountRef.current = 0 // Reset error count on success
    } catch (err) {
      errorCountRef.current++
      if (err.name === 'AbortError') {
        setError('Request timeout - server may be under heavy load')
      } else {
        setError(`${err.message} (attempt ${errorCountRef.current})`)
      }
      // Don't clear events on error - graceful degradation
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const getThreatLevelName = (level) => {
    const names = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    return names[level] || 'UNKNOWN'
  }

  const getThreatLevelBadge = (level) => {
    const badges = {
      0: 'bg-gray-100 text-gray-800',
      1: 'bg-blue-100 text-blue-800',
      2: 'bg-yellow-100 text-yellow-800',
      3: 'bg-orange-100 text-orange-800',
      4: 'bg-red-100 text-red-800',
    }
    return badges[level] || 'bg-gray-100 text-gray-800'
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 p-2.5 rounded-lg shadow-md">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Security Events Monitor</h2>
          </div>
          <div className="flex items-center space-x-4">
            <label className="flex items-center text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="mr-2 rounded"
              />
              Auto-refresh (5s)
            </label>
            <button
              onClick={fetchEvents}
              disabled={loading}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 shadow-md transition-all duration-200"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Min Threat Level
            </label>
            <select
              value={filters.min_threat_level}
              onChange={(e) => handleFilterChange('min_threat_level', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={0}>All (INFO+)</option>
              <option value={1}>LOW+</option>
              <option value={2}>MEDIUM+</option>
              <option value={3}>HIGH+</option>
              <option value={4}>CRITICAL only</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Threat Type
            </label>
            <input
              type="text"
              value={filters.threat_type}
              onChange={(e) => handleFilterChange('threat_type', e.target.value)}
              placeholder="e.g., api_abuse"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source ID
            </label>
            <input
              type="text"
              value={filters.source_id}
              onChange={(e) => handleFilterChange('source_id', e.target.value)}
              placeholder="Filter by source"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Limit
            </label>
            <select
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </div>
        </div>

        {/* Error Display - non-blocking */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="text-yellow-600 mr-2">⚠️</span>
                <div>
                  <p className="text-yellow-800 text-sm font-medium">{error}</p>
                  <p className="text-yellow-600 text-xs mt-1">
                    {events.length > 0 ? 'Showing last successful data. System will retry automatically.' : 'Retrying...'}
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

        {/* Events Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Threat Level
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Review
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    {loading ? 'Loading events...' : 'No security events found'}
                  </td>
                </tr>
              ) : (
                events.map((event, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                      {formatTimestamp(event.timestamp)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getThreatLevelBadge(
                          event.threat_level
                        )}`}
                      >
                        {getThreatLevelName(event.threat_level)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{event.threat_type}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                      {event.source_identifier}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{event.description}</td>
                    <td className="px-4 py-3 text-sm">
                      {event.requires_review ? (
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                          Required
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Summary */}
        {events.length > 0 && (
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <span>Showing {events.length} event(s)</span>
            <span className="inline-flex items-center">
              <span className={`w-2 h-2 rounded-full mr-2 ${error ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`}></span>
              {lastUpdate && `Last updated: ${lastUpdate.toLocaleTimeString()}`}
            </span>
          </div>
        )}
      </div>

      {/* Event Statistics */}
      {events.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg p-6 text-white">
            <p className="text-sm opacity-90 mb-2">Total Events</p>
            <p className="text-4xl font-bold">{events.length}</p>
            <div className="mt-3 flex items-center text-xs opacity-75">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              Live monitoring
            </div>
          </div>

          <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl shadow-lg p-6 text-white">
            <p className="text-sm opacity-90 mb-2">Requiring Review</p>
            <p className="text-4xl font-bold">
              {events.filter((e) => e.requires_review).length}
            </p>
            <div className="mt-3 flex items-center text-xs opacity-75">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Needs analyst attention
            </div>
          </div>

          <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl shadow-lg p-6 text-white">
            <p className="text-sm opacity-90 mb-2">Critical Events</p>
            <p className="text-4xl font-bold">
              {events.filter((e) => e.threat_level === 4).length}
            </p>
            <div className="mt-3 flex items-center text-xs opacity-75">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              High priority
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SecurityMonitor

import { useState, useEffect } from 'react'
import { ENDPOINTS } from '../config'

function SecurityMonitor() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    limit: 50,
    min_threat_level: 0,
    threat_type: '',
    source_id: '',
  })
  const [autoRefresh, setAutoRefresh] = useState(false)

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

      const response = await fetch(`${ENDPOINTS.securityEvents}?${params}`)
      if (!response.ok) throw new Error('Failed to fetch events')

      const data = await response.json()
      setEvents(data)
    } catch (err) {
      setError(err.message)
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
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Security Events Monitor</h2>
          <div className="flex items-center space-x-4">
            <label className="flex items-center text-sm text-gray-700">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="mr-2"
              />
              Auto-refresh (5s)
            </label>
            <button
              onClick={fetchEvents}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
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

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-800 text-sm">{error}</p>
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
          <div className="mt-4 text-sm text-gray-600">
            Showing {events.length} event(s) • Last updated: {new Date().toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Event Statistics */}
      {events.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500 mb-1">Total Events</p>
            <p className="text-2xl font-bold text-gray-900">{events.length}</p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500 mb-1">Requiring Review</p>
            <p className="text-2xl font-bold text-yellow-600">
              {events.filter((e) => e.requires_review).length}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500 mb-1">Critical Events</p>
            <p className="text-2xl font-bold text-red-600">
              {events.filter((e) => e.threat_level === 4).length}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default SecurityMonitor

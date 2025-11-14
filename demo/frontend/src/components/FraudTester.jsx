import { useState } from 'react'
import { ENDPOINTS } from '../config'

const SAMPLE_SCENARIOS = {
  normal: {
    name: 'Normal Transaction',
    transaction: {
      user_id: 'user_12345',
      device_id: 'device_xyz',
      amount: 50.0,
      timestamp: new Date().toISOString(),
      location: 'New York, US',
      merchant_id: 'merchant_abc',
      ip_address: '192.168.1.1',
      card_last4: '4242',
      transaction_type: 'purchase',
    },
  },
  highAmount: {
    name: 'High Amount Transaction',
    transaction: {
      user_id: 'user_12345',
      device_id: 'device_xyz',
      amount: 5000.0,
      timestamp: new Date().toISOString(),
      location: 'New York, US',
      merchant_id: 'merchant_abc',
      ip_address: '192.168.1.1',
      card_last4: '4242',
      transaction_type: 'purchase',
    },
  },
  foreignLocation: {
    name: 'Foreign Location',
    transaction: {
      user_id: 'user_12345',
      device_id: 'device_xyz',
      amount: 150.0,
      timestamp: new Date().toISOString(),
      location: 'Tokyo, JP',
      merchant_id: 'merchant_xyz',
      ip_address: '203.0.113.42',
      card_last4: '4242',
      transaction_type: 'purchase',
    },
  },
  suspiciousPattern: {
    name: 'Suspicious Pattern',
    transaction: {
      user_id: 'user_12345',
      device_id: 'new_device_123',
      amount: 999.99,
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 AM
      location: 'Unknown',
      merchant_id: 'merchant_suspicious',
      ip_address: '203.0.113.100',
      card_last4: '4242',
      transaction_type: 'purchase',
    },
  },
  custom: {
    name: 'Custom Transaction',
    transaction: {
      user_id: '',
      device_id: '',
      amount: 0,
      timestamp: new Date().toISOString(),
      location: '',
      merchant_id: '',
      ip_address: '',
      card_last4: '',
      transaction_type: 'purchase',
    },
  },
}

function FraudTester() {
  const [selectedScenario, setSelectedScenario] = useState('normal')
  const [transaction, setTransaction] = useState(SAMPLE_SCENARIOS.normal.transaction)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleScenarioChange = (scenarioKey) => {
    setSelectedScenario(scenarioKey)
    setTransaction({ ...SAMPLE_SCENARIOS[scenarioKey].transaction })
    setResult(null)
    setError(null)
  }

  const handleInputChange = (field, value) => {
    setTransaction((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Update timestamp to current time
      const txn = {
        ...transaction,
        timestamp: new Date().toISOString(),
        amount: parseFloat(transaction.amount),
      }

      const response = await fetch(ENDPOINTS.decision, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(txn),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Request failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getDecisionName = (code) => {
    const names = {
      0: 'ALLOW',
      1: 'MONITOR',
      2: 'STEP-UP AUTH',
      3: 'REVIEW',
      4: 'BLOCK',
    }
    return names[code] || 'UNKNOWN'
  }

  const getDecisionColor = (code) => {
    const colors = {
      0: 'bg-green-100 text-green-800 border-green-300',
      1: 'bg-blue-100 text-blue-800 border-blue-300',
      2: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      3: 'bg-orange-100 text-orange-800 border-orange-300',
      4: 'bg-red-100 text-red-800 border-red-300',
    }
    return colors[code] || 'bg-gray-100 text-gray-800 border-gray-300'
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Transaction Fraud Decision Tester</h2>
        <p className="text-sm text-gray-600 mb-6">
          Test the fraud detection pipeline by sending sample or custom transactions to the /v1/decision endpoint.
        </p>

        {/* Scenario Selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Scenario
          </label>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Object.entries(SAMPLE_SCENARIOS).map(([key, scenario]) => (
              <button
                key={key}
                onClick={() => handleScenarioChange(key)}
                className={`px-4 py-2 text-sm font-medium rounded-md border ${
                  selectedScenario === key
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                {scenario.name}
              </button>
            ))}
          </div>
        </div>

        {/* Transaction Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                User ID
              </label>
              <input
                type="text"
                value={transaction.user_id}
                onChange={(e) => handleInputChange('user_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device ID
              </label>
              <input
                type="text"
                value={transaction.device_id}
                onChange={(e) => handleInputChange('device_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Amount
              </label>
              <input
                type="number"
                step="0.01"
                value={transaction.amount}
                onChange={(e) => handleInputChange('amount', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                type="text"
                value={transaction.location}
                onChange={(e) => handleInputChange('location', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Merchant ID
              </label>
              <input
                type="text"
                value={transaction.merchant_id}
                onChange={(e) => handleInputChange('merchant_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                IP Address
              </label>
              <input
                type="text"
                value={transaction.ip_address}
                onChange={(e) => handleInputChange('ip_address', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Card Last 4
              </label>
              <input
                type="text"
                maxLength={4}
                value={transaction.card_last4}
                onChange={(e) => handleInputChange('card_last4', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Transaction Type
              </label>
              <select
                value={transaction.transaction_type}
                onChange={(e) => handleInputChange('transaction_type', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="purchase">Purchase</option>
                <option value="withdrawal">Withdrawal</option>
                <option value="transfer">Transfer</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Test Transaction'}
            </button>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Result</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className={`border-2 rounded-lg p-4 ${getDecisionColor(result.decision_code)}`}>
              <p className="text-sm font-medium mb-1">Decision</p>
              <p className="text-2xl font-bold">{getDecisionName(result.decision_code)}</p>
              <p className="text-xs mt-1">Code: {result.decision_code}</p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-1">Fraud Score</p>
              <p className="text-2xl font-bold text-gray-900">
                {(result.score * 100).toFixed(1)}%
              </p>
              {result.ml_score !== null && (
                <p className="text-xs text-gray-600 mt-1">
                  ML Score: {(result.ml_score * 100).toFixed(1)}%
                </p>
              )}
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-1">Latency</p>
              <p className="text-2xl font-bold text-gray-900">{result.latency_ms}ms</p>
              <p className="text-xs text-gray-600 mt-1">
                Target: &lt;90ms P99
              </p>
            </div>
          </div>

          {/* Rule Flags */}
          {result.rule_flags && result.rule_flags.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Rule Flags</p>
              <div className="flex flex-wrap gap-2">
                {result.rule_flags.map((flag, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reasons */}
          {result.reasons && result.reasons.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Reasons</p>
              <ul className="list-disc list-inside space-y-1">
                {result.reasons.map((reason, idx) => (
                  <li key={idx} className="text-sm text-gray-600">
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Top Features */}
          {result.top_features && result.top_features.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Top Contributing Features</p>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Feature</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Contribution</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {result.top_features.slice(0, 5).map((feature, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-2 text-sm text-gray-900">{feature.name}</td>
                        <td className="px-4 py-2 text-sm text-gray-600">{feature.value?.toFixed(3)}</td>
                        <td className="px-4 py-2">
                          <div className="flex items-center">
                            <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                              <div
                                className="bg-blue-500 h-2 rounded-full"
                                style={{
                                  width: `${Math.abs(feature.contribution || 0) * 100}%`,
                                }}
                              />
                            </div>
                            <span className="text-xs text-gray-600">
                              {((feature.contribution || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FraudTester

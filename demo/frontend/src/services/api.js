/**
 * Centralized API Client
 *
 * Provides consistent API calling with:
 * - Timeout handling
 * - Error normalization
 * - Request/response logging (optional)
 */

import { API_BASE_URL, ENDPOINTS } from '../config'

/**
 * Default timeout for API requests (5 seconds)
 */
const DEFAULT_TIMEOUT = 5000

/**
 * Fetch with timeout support
 *
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return response
  } catch (err) {
    clearTimeout(timeoutId)
    throw err
  }
}

/**
 * Normalize error from API call
 *
 * @param {Error} error - Original error
 * @returns {Error} Normalized error with user-friendly message
 */
function normalizeError(error) {
  if (error.name === 'AbortError') {
    const timeoutError = new Error('Request timed out. Please try again.')
    timeoutError.code = 'TIMEOUT'
    return timeoutError
  }

  if (error.message && error.message.includes('fetch')) {
    const networkError = new Error('Network error. Check your connection.')
    networkError.code = 'NETWORK_ERROR'
    return networkError
  }

  return error
}

/**
 * Make a GET request
 *
 * @param {string} url - URL to fetch
 * @param {object} options - Additional options
 * @returns {Promise<object>} Response data
 */
export async function get(url, options = {}) {
  try {
    console.log('🔍 API GET Request:', { url })

    const response = await fetchWithTimeout(url, {
      method: 'GET',
      ...options,
    })

    console.log('✅ API GET Response Status:', response.status)

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  } catch (err) {
    console.error('❌ API GET Request Failed:', err)
    throw normalizeError(err)
  }
}

/**
 * Make a POST request
 *
 * @param {string} url - URL to post to
 * @param {object} data - Request body
 * @param {object} options - Additional options
 * @returns {Promise<object>} Response data
 */
export async function post(url, data, options = {}) {
  try {
    // Destructure options to prevent body override
    const { headers: optionHeaders, ...restOptions } = options

    // Debug logging
    console.log('🔍 API POST Request:', {
      url,
      data: JSON.stringify(data).substring(0, 200),
      headers: optionHeaders,
    })

    const response = await fetchWithTimeout(url, {
      ...restOptions,  // Spread other options first (e.g., signal)
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...optionHeaders,
      },
      body: JSON.stringify(data),  // Body set last, cannot be overridden
    })

    console.log('✅ API Response Status:', response.status)

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      console.error('❌ API Error Response:', errorData)

      // Handle FastAPI validation errors (returns array of errors)
      if (Array.isArray(errorData?.detail)) {
        const messages = errorData.detail.map(err => {
          const field = Array.isArray(err.loc) ? err.loc.join('.') : 'field'
          return `${field}: ${err.msg}`
        }).join('; ')
        throw new Error(messages)
      }

      // Handle simple error messages
      const message = errorData?.detail || errorData?.message || `HTTP ${response.status}`
      throw new Error(message)
    }

    return await response.json()
  } catch (err) {
    console.error('❌ API Request Failed:', err)
    throw normalizeError(err)
  }
}

/**
 * API Service - specific endpoint methods
 */
export const api = {
  // Fraud Detection
  async makeFraudDecision(transaction, sourceId = null) {
    const headers = sourceId ? { 'X-Source-ID': sourceId } : {}
    return post(ENDPOINTS.decision, transaction, { headers })
  },

  async getDecisionHealth() {
    return get(ENDPOINTS.decisionHealth)
  },

  // Security Events
  async getSecurityEvents(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.min_threat_level) queryParams.append('min_threat_level', params.min_threat_level)
    if (params.threat_type) queryParams.append('threat_type', params.threat_type)
    if (params.source_id) queryParams.append('source_id', params.source_id)

    const url = `${ENDPOINTS.securityEvents}?${queryParams}`
    return get(url)
  },

  async getReviewQueue(limit = 100) {
    return get(`${ENDPOINTS.reviewQueue}?limit=${limit}`)
  },

  async reviewEvent(eventId, reviewData) {
    return post(ENDPOINTS.reviewEvent(eventId), reviewData)
  },

  async getSourceRisk(sourceId) {
    return get(ENDPOINTS.sourceRisk(sourceId))
  },

  async getBlockedSources() {
    return get(ENDPOINTS.blockedSources)
  },

  async unblockSource(sourceId, analystId, reason = null) {
    return post(ENDPOINTS.unblockSource(sourceId), {
      source_id: sourceId,
      analyst_id: analystId,
      reason,
    })
  },

  async getAuditTrail(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.source_id) queryParams.append('source_id', params.source_id)
    if (params.resource) queryParams.append('resource', params.resource)
    if (params.limit) queryParams.append('limit', params.limit)

    const url = `${ENDPOINTS.auditTrail}?${queryParams}`
    return get(url)
  },

  async getSecurityDashboard() {
    return get(ENDPOINTS.securityDashboard)
  },

  async getSecurityHealth() {
    return get(ENDPOINTS.securityHealth)
  },

  // Rate Limiting
  async getRateLimitStatus(sourceId) {
    return get(ENDPOINTS.rateLimitStatus(sourceId))
  },

  async setRateLimitTier(sourceId, tier, analystId) {
    return post(`${ENDPOINTS.setRateLimitTier(sourceId)}?tier=${tier}&analyst_id=${analystId}`)
  },
}

export default api

// API Configuration
// Change this if your backend is running on a different host/port
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const ENDPOINTS = {
  // Fraud Decision
  decision: `${API_BASE_URL}/v1/decision`,
  decisionHealth: `${API_BASE_URL}/v1/decision/health`,

  // Security
  securityEvents: `${API_BASE_URL}/v1/security/events`,
  reviewQueue: `${API_BASE_URL}/v1/security/events/review-queue`,
  reviewEvent: (id) => `${API_BASE_URL}/v1/security/events/${id}/review`,
  sourceRisk: (id) => `${API_BASE_URL}/v1/security/sources/${id}/risk`,
  blockedSources: `${API_BASE_URL}/v1/security/sources/blocked`,
  unblockSource: (id) => `${API_BASE_URL}/v1/security/sources/${id}/unblock`,
  auditTrail: `${API_BASE_URL}/v1/security/audit-trail`,
  securityDashboard: `${API_BASE_URL}/v1/security/dashboard`,
  securityHealth: `${API_BASE_URL}/v1/security/health`,

  // Rate Limiting
  rateLimitStatus: (id) => `${API_BASE_URL}/v1/security/rate-limits/${id}`,
  setRateLimitTier: (id) => `${API_BASE_URL}/v1/security/rate-limits/${id}/tier`,
};

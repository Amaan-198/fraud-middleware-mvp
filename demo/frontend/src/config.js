// API Configuration
// Use Vite proxy (relative URLs) to avoid CORS issues
// Vite dev server will proxy /v1/* requests to http://localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

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

  // Session Monitoring
  sessionsActive: `${API_BASE_URL}/v1/sessions/active`,
  sessionDetail: (id) => `${API_BASE_URL}/v1/sessions/${id}`,
  sessionRisk: (id) => `${API_BASE_URL}/v1/sessions/${id}/risk`,
  sessionTerminate: (id) => `${API_BASE_URL}/v1/sessions/${id}/terminate`,
  sessionsSuspicious: `${API_BASE_URL}/v1/sessions/suspicious`,
  sessionsHealth: `${API_BASE_URL}/v1/sessions/health`,

  // Demo Sessions
  demoSessionScenario: `${API_BASE_URL}/v1/demo/session-scenario`,
  demoSessionComparison: `${API_BASE_URL}/v1/demo/session-comparison`,
};

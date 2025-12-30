export function getToken(): string | null { return localStorage.getItem('agent_bearer_token') || null }
export function setToken(t: string) { localStorage.setItem('agent_bearer_token', t) }
export function clearToken() { localStorage.removeItem('agent_bearer_token') }
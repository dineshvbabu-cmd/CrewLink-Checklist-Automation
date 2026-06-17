import axios from 'axios'
import type {
  AICheckResult,
  AuthUser,
  AuditEntry,
  ConfirmationItem,
  CrewMember,
  CrewReport,
  DocumentsData,
  ExtractionReport,
  IntegrationStatus,
  LoginResponse,
  MatrixReport,
  PortalBatchResult,
  PortalVerificationResult,
  SelfServicePacket,
  Vessel,
} from './types'

const BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL: BASE })
let authToken = ''

export function setAuthToken(token: string | null) {
  authToken = token || ''
  if (authToken) {
    api.defaults.headers.common.Authorization = `Bearer ${authToken}`
  } else {
    delete api.defaults.headers.common.Authorization
  }
}

export const getExportChecklistUrl = (crewId: string) => `${BASE}/crew/${crewId}/export-checklist`
export const login = (username: string, password: string): Promise<LoginResponse> => api.post('/auth/login', { username, password }).then(response => response.data)
export const getCurrentUser = (): Promise<AuthUser> => api.get('/auth/me').then(response => response.data)
export const logout = (): Promise<{ ok: boolean }> => api.post('/auth/logout').then(response => response.data)
export const getIntegrationStatus = (): Promise<IntegrationStatus> => api.get('/integrations/status').then(response => response.data)

export const getVessel = (): Promise<Vessel> => api.get('/vessel').then(response => response.data)
export const getCrew = (): Promise<CrewMember[]> => api.get('/crew').then(response => response.data)
export const getCrewMember = (id: string): Promise<CrewMember> => api.get(`/crew/${id}`).then(response => response.data)
export const getDocuments = (id: string): Promise<DocumentsData> => api.get(`/crew/${id}/documents`).then(response => response.data)
export const getConfirmation = (id: string): Promise<ConfirmationItem[]> => api.get(`/crew/${id}/confirmation`).then(response => response.data)
export const getAuditLog = (id: string): Promise<AuditEntry[]> => api.get(`/crew/${id}/audit-log`).then(response => response.data)
export const getMatrix = (id: string): Promise<MatrixReport> => api.get(`/crew/${id}/matrix`).then(response => response.data)
export const getExtraction = (id: string): Promise<ExtractionReport> => api.get(`/crew/${id}/extraction`).then(response => response.data)
export const getCrewReport = (id: string): Promise<CrewReport> => api.get(`/crew/${id}/report`).then(response => response.data)
export const getLatestSelfServiceLink = (id: string): Promise<SelfServicePacket | null> => api.get(`/crew/${id}/self-service/latest`).then(response => response.data)
export const getSelfServicePacket = (token: string): Promise<SelfServicePacket> => api.get(`/self-service/${token}`).then(response => response.data)
export const runAICheck = (id: string): Promise<AICheckResult> => api.post(`/ai/check/${id}`).then(response => response.data)
export const runBatchAICheck = (crewIds: string[]): Promise<{ results: AICheckResult[] }> => api.post('/ai/check-batch', { crewIds }).then(response => response.data)
export const verifyPortal = (id: string, docName: string, docNo: string): Promise<PortalVerificationResult> =>
  api.post(`/crew/${id}/verify-portal`, { docName, docNo }).then(response => response.data)
export const verifyPortalBatch = (id: string): Promise<PortalBatchResult> =>
  api.post(`/crew/${id}/verify-portal-batch`).then(response => response.data)
export const updateDocumentRemark = (crewId: string, srNo: number, remark: string, actor = 'RC Officer') =>
  api.post(`/crew/${crewId}/documents/${srNo}/remark`, { remark, actor }).then(response => response.data)
export const overrideDocumentStatus = (crewId: string, srNo: number, status: 'green' | 'yellow' | 'red', reason: string, actor = 'RC Officer') =>
  api.post(`/crew/${crewId}/documents/${srNo}/override`, { status, reason, actor }).then(response => response.data)
export const uploadDocumentAttachment = (crewId: string, srNo: number, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/crew/${crewId}/documents/${srNo}/attachment`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(response => response.data)
}
export const updateConfirmationItem = (crewId: string, srNo: number, verifyOps: boolean, officeRemark: string) =>
  api.post(`/crew/${crewId}/confirmation/${srNo}`, { verifyOps, officeRemark }).then(response => response.data)
export const sendSelfServiceLink = (crewId: string, sentBy = 'RC Officer'): Promise<SelfServicePacket> =>
  api.post(`/crew/${crewId}/self-service/send`, { sentBy }).then(response => response.data)
export const submitSelfServicePacket = (
  token: string,
  payload: {
    seafarerName: string
    items: Array<{ srNo: number; verifyCrew: boolean; seafarerRemark: string }>
  },
): Promise<SelfServicePacket> => api.post(`/self-service/${token}/submit`, payload).then(response => response.data)

if (typeof window !== 'undefined') {
  setAuthToken(window.localStorage.getItem('crewlink_auth_token'))
}

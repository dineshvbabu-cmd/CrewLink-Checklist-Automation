export type AIStatus = 'green' | 'yellow' | 'red' | 'grey'

export interface Vessel {
  id: string
  name: string
  type: string
  imo: string
  flag: string
  totalCrew: number
  reliefOverdue: number
  dueOneMonth: number
  extraCrew: number
  extendedContract: number
  reducedContract: number
}

export interface CrewMember {
  id: string
  srNo: number
  rank: string
  name: string
  empNo: string
  nationality: string
  travelDate: string
  signOnDate: string
  reliefDue: string
  relieverRank: string
  relieverName: string
  relieverApproved: boolean
  aiStatus: Exclude<AIStatus, 'grey'>
  complianceIssue: boolean
  status: 'planned' | 'onboard'
}

export interface DocumentItem {
  srNo: number
  name: string
  docNo: string
  type: string
  issueDate: string
  expiryDate: string
  verifiedRC: boolean
  verifiedOps: boolean
  portalVerified?: boolean
  aiStatus: Exclude<AIStatus, 'grey'>
  remark: string
  missing: boolean
  required?: boolean
  attachmentUrl?: string
  attachmentName?: string
  overrideStatus?: string
  overrideReason?: string
  extractionConfidence?: number
  expired?: boolean
}

export interface DocumentSection {
  title: string
  items: DocumentItem[]
}

export interface ChecklistSummary {
  valid: number
  pendingVerification: number
  missing: number
  expired: number
}

export interface DocumentsData {
  summary: ChecklistSummary
  sections: DocumentSection[]
}

export interface ConfirmationItem {
  srNo: number
  description: string
  verifyOps: boolean
  officeRemark: string
  verifyCrew: boolean
  seafarerRemark: string
}

export interface PortalVerificationResult {
  docName: string
  verified: boolean
  message: string
  portal: string
}

export interface PortalBatchResult {
  crewId: string
  verifiedCount: number
  failedCount: number
  results: PortalVerificationResult[]
  summary: ChecklistSummary
}

export interface ExtractedDocument {
  srNo: number
  name: string
  section: string
  confidence: number
  matchedToMatrix: boolean
  sourceFile: string
  status: Exclude<AIStatus, 'grey'>
}

export interface ExtractionReport {
  crewId: string
  crewName: string
  rank: string
  requiredDocuments: string[]
  extractedDocuments: ExtractedDocument[]
}

export interface MatrixReport {
  crewId: string
  vessel: string
  rank: string
  requiredDocuments: string[]
}

export interface AuditEntry {
  id: string
  timestamp: string
  actor: string
  action: string
  target: string
  message: string
}

export interface SelfServicePacket {
  token: string
  crewId: string
  crewName: string
  rank: string
  status: 'sent' | 'submitted'
  sentAt: string
  sentBy: string
  submittedAt?: string
  submittedBy?: string
  url: string
  items: ConfirmationItem[]
}

export interface AuthUser {
  id: string
  username: string
  fullName: string
  role: 'admin' | 'rc' | 'ops'
  token?: string
}

export interface LoginResponse {
  token: string
  user: AuthUser
}

export interface IntegrationStatus {
  portal: {
    provider: string
    configured: boolean
    mode: 'mock' | 'external'
  }
  ai: {
    provider: string
    configured: boolean
    model: string
    mode: 'external' | 'fallback'
  }
  storage: {
    databasePath: string
    uploadsPath: string
  }
  user: string
}

export interface CrewReport {
  matrix: {
    requiredDocuments: string[]
    vessel: string
  }
  extraction: ExtractionReport
  auditLog: AuditEntry[]
  latestSelfServiceLink: SelfServicePacket | null
  learningFeedbackCount: number
}

export interface AICheckResult {
  crewId: string
  name: string
  rank: string
  vessel: string
  flag: string
  summary: ChecklistSummary
  missingItems: string[]
  pendingItems: string[]
  expiredItems: string[]
  aiNarrative: string
  overallStatus: Exclude<AIStatus, 'grey'>
  matrixDocuments: string[]
  extractedDocuments: ExtractedDocument[]
}

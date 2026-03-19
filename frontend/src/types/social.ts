export interface Contact {
  id: string
  name: string
  phone?: string
  email?: string
  notes?: string
  created_at: string
}

export interface ContactListResponse {
  items: Contact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SplitParticipant {
  contact_id: string
  contact_name: string
  share_amount: number
  paid_amount: number
  is_settled: boolean
}

export interface SplitBill {
  id: string
  title: string
  total_amount: number
  payer_contact_id: string
  status: 'pending' | 'partial' | 'settled'
  participants: SplitParticipant[]
  notes?: string
  created_at: string
}

export interface SplitBillListResponse {
  items: SplitBill[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SplitGroup {
  id: string
  name: string
  description?: string
  member_count: number
  total_amount: number
  created_at: string
}

export interface SplitGroupListResponse {
  items: SplitGroup[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface NetBalance {
  contact_id: string
  contact_name: string
  they_owe_me: number
  i_owe_them: number
  net: number
}

export interface SettlementSummary {
  total_owed_to_me: number
  total_i_owe: number
  net_position: number
  unsettled_bills_count: number
}

export interface CreateContactPayload {
  name: string
  phone?: string
  email?: string
  notes?: string
}

export interface UpdateContactPayload {
  name?: string
  phone?: string
  email?: string
  notes?: string
}

export interface SplitParticipantInput {
  contact_id: string
  share_amount: number
  already_paid?: boolean
}

export interface CreateSplitBillPayload {
  title: string
  total_amount: number
  payer_contact_id: string
  group_id?: string
  splits: SplitParticipantInput[]
  transaction_id?: string
  notes?: string
}

export interface SettleParticipantPayload {
  contact_id: string
  amount: number
}

export interface CreateSplitGroupPayload {
  name: string
  description?: string
  contact_ids?: string[]
}

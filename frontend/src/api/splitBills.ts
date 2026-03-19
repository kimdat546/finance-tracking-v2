import client from '@/api/client'
import type {
  Contact,
  ContactListResponse,
  CreateContactPayload,
  CreateSplitBillPayload,
  CreateSplitGroupPayload,
  NetBalance,
  SettleParticipantPayload,
  SettlementSummary,
  SplitBill,
  SplitBillListResponse,
  SplitGroup,
  SplitGroupListResponse,
  UpdateContactPayload,
} from '@/types/social'

// ---------------------------------------------------------------------------
// Contacts
// ---------------------------------------------------------------------------

export const getContacts = async (
  userId: string,
  params?: { search?: string; page?: number; page_size?: number }
): Promise<ContactListResponse> => {
  const response = await client.get<ContactListResponse>('/contacts', {
    params: { user_id: userId, ...params },
  })
  return response.data
}

export const createContact = async (
  userId: string,
  payload: CreateContactPayload
): Promise<Contact> => {
  const response = await client.post<Contact>('/contacts', payload, {
    params: { user_id: userId },
  })
  return response.data
}

export const updateContact = async (
  userId: string,
  contactId: string,
  payload: UpdateContactPayload
): Promise<Contact> => {
  const response = await client.put<Contact>(`/contacts/${contactId}`, payload, {
    params: { user_id: userId },
  })
  return response.data
}

export const deleteContact = async (userId: string, contactId: string): Promise<void> => {
  await client.delete(`/contacts/${contactId}`, {
    params: { user_id: userId },
  })
}

// ---------------------------------------------------------------------------
// Split Groups
// ---------------------------------------------------------------------------

export const getSplitGroups = async (
  userId: string,
  params?: { page?: number; page_size?: number }
): Promise<SplitGroupListResponse> => {
  const response = await client.get<SplitGroupListResponse>('/split-bills/groups', {
    params: { user_id: userId, ...params },
  })
  return response.data
}

export const createSplitGroup = async (
  userId: string,
  payload: CreateSplitGroupPayload
): Promise<SplitGroup> => {
  const response = await client.post<SplitGroup>('/split-bills/groups', payload, {
    params: { user_id: userId },
  })
  return response.data
}

// ---------------------------------------------------------------------------
// Split Bills
// ---------------------------------------------------------------------------

export const getSplitBills = async (
  userId: string,
  params?: { group_id?: string; page?: number; page_size?: number }
): Promise<SplitBillListResponse> => {
  const response = await client.get<SplitBillListResponse>('/split-bills', {
    params: { user_id: userId, ...params },
  })
  return response.data
}

export const createSplitBill = async (
  userId: string,
  payload: CreateSplitBillPayload
): Promise<SplitBill> => {
  const response = await client.post<SplitBill>('/split-bills', payload, {
    params: { user_id: userId },
  })
  return response.data
}

export const settleSplitBill = async (
  userId: string,
  billId: string,
  payload: SettleParticipantPayload
): Promise<SplitBill> => {
  const response = await client.post<SplitBill>(`/split-bills/${billId}/settle`, payload, {
    params: { user_id: userId },
  })
  return response.data
}

// ---------------------------------------------------------------------------
// Balances & Summary
// ---------------------------------------------------------------------------

export const getNetBalances = async (userId: string): Promise<NetBalance[]> => {
  const response = await client.get<NetBalance[]>('/split-bills/balances', {
    params: { user_id: userId },
  })
  return response.data
}

export const getSettlementSummary = async (userId: string): Promise<SettlementSummary> => {
  const response = await client.get<SettlementSummary>('/split-bills/summary', {
    params: { user_id: userId },
  })
  return response.data
}

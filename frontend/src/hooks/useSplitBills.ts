import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createContact,
  createSplitBill,
  createSplitGroup,
  deleteContact,
  getContacts,
  getNetBalances,
  getSettlementSummary,
  getSplitBills,
  getSplitGroups,
  settleSplitBill,
  updateContact,
} from '@/api/splitBills'
import { getCurrentUserId } from '@/api/client'
import type {
  CreateContactPayload,
  CreateSplitBillPayload,
  CreateSplitGroupPayload,
  SettleParticipantPayload,
  UpdateContactPayload,
} from '@/types/social'

// ---------------------------------------------------------------------------
// User ID from centralized auth helper
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export const useContacts = (search?: string) => {
  return useQuery({
    queryKey: ['contacts', search],
    queryFn: () => getContacts(getCurrentUserId(), { search }),
  })
}

export const useSplitBills = (groupId?: string) => {
  return useQuery({
    queryKey: ['split-bills', groupId],
    queryFn: () => getSplitBills(getCurrentUserId(), { group_id: groupId }),
  })
}

export const useSplitGroups = () => {
  return useQuery({
    queryKey: ['split-groups'],
    queryFn: () => getSplitGroups(getCurrentUserId()),
  })
}

export const useNetBalances = () => {
  return useQuery({
    queryKey: ['net-balances'],
    queryFn: () => getNetBalances(getCurrentUserId()),
  })
}

export const useSettlementSummary = () => {
  return useQuery({
    queryKey: ['settlement-summary'],
    queryFn: () => getSettlementSummary(getCurrentUserId()),
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export const useCreateContact = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateContactPayload) => createContact(getCurrentUserId(), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
    },
  })
}

export const useUpdateContact = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ contactId, payload }: { contactId: string; payload: UpdateContactPayload }) =>
      updateContact(getCurrentUserId(), contactId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
    },
  })
}

export const useDeleteContact = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (contactId: string) => deleteContact(getCurrentUserId(), contactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
    },
  })
}

export const useCreateSplitBill = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateSplitBillPayload) => createSplitBill(getCurrentUserId(), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['split-bills'] })
      queryClient.invalidateQueries({ queryKey: ['net-balances'] })
      queryClient.invalidateQueries({ queryKey: ['settlement-summary'] })
    },
  })
}

export const useSettleSplitBill = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      billId,
      payload,
    }: {
      billId: string
      payload: SettleParticipantPayload
    }) => settleSplitBill(getCurrentUserId(), billId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['split-bills'] })
      queryClient.invalidateQueries({ queryKey: ['net-balances'] })
      queryClient.invalidateQueries({ queryKey: ['settlement-summary'] })
    },
  })
}

export const useCreateSplitGroup = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateSplitGroupPayload) => createSplitGroup(getCurrentUserId(), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['split-groups'] })
    },
  })
}

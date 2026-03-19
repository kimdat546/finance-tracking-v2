import { create } from 'zustand';

export type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

interface SyncState {
  status: SyncStatus;
  lastSyncAt: string | null;
  lastError: string | null;
  syncedCount: number;
  connectedAccounts: string[];

  setStatus: (status: SyncStatus) => void;
  setSyncResult: (syncedCount: number, error?: string) => void;
  addConnectedAccount: (accountId: string) => void;
  removeConnectedAccount: (accountId: string) => void;
  reset: () => void;
}

export const useSyncStore = create<SyncState>((set) => ({
  status: 'idle',
  lastSyncAt: null,
  lastError: null,
  syncedCount: 0,
  connectedAccounts: [],

  setStatus: (status) => set({ status }),

  setSyncResult: (syncedCount, error) =>
    set({
      status: error ? 'error' : 'success',
      lastSyncAt: new Date().toISOString(),
      lastError: error ?? null,
      syncedCount,
    }),

  addConnectedAccount: (accountId) =>
    set((s) => ({
      connectedAccounts: [...new Set([...s.connectedAccounts, accountId])],
    })),

  removeConnectedAccount: (accountId) =>
    set((s) => ({
      connectedAccounts: s.connectedAccounts.filter((id) => id !== accountId),
    })),

  reset: () =>
    set({ status: 'idle', lastSyncAt: null, lastError: null, syncedCount: 0 }),
}));

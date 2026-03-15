import { create } from 'zustand'

interface AppState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  pendingReviewCount: number
  setPendingReviewCount: (count: number) => void
  incrementPendingReviewCount: () => void
  decrementPendingReviewCount: () => void

  notificationCount: number
  setNotificationCount: (count: number) => void

  syncStatus: 'idle' | 'syncing' | 'success' | 'error'
  setSyncStatus: (status: 'idle' | 'syncing' | 'success' | 'error') => void
  lastSyncTime?: Date
  setLastSyncTime: (time: Date) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  pendingReviewCount: 0,
  setPendingReviewCount: (count) => set({ pendingReviewCount: count }),
  incrementPendingReviewCount: () =>
    set((state) => ({ pendingReviewCount: state.pendingReviewCount + 1 })),
  decrementPendingReviewCount: () =>
    set((state) => ({
      pendingReviewCount: Math.max(0, state.pendingReviewCount - 1),
    })),

  notificationCount: 0,
  setNotificationCount: (count) => set({ notificationCount: count }),

  syncStatus: 'idle',
  setSyncStatus: (status) => set({ syncStatus: status }),
  setLastSyncTime: (time) => set({ lastSyncTime: time }),
}))

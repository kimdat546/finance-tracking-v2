import React, { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui'
import { useContacts, useCreateSplitBill } from '@/hooks/useSplitBills'
import type { CreateSplitBillPayload, SplitParticipantInput } from '@/types/social'

interface CreateBillModalProps {
  onClose: () => void
  onSuccess?: () => void
}

interface ParticipantRow {
  contact_id: string
  share_amount: string
}

export const CreateBillModal: React.FC<CreateBillModalProps> = ({ onClose, onSuccess }) => {
  const { data: contactsData } = useContacts()
  const createBill = useCreateSplitBill()

  const [title, setTitle] = useState('')
  const [totalAmount, setTotalAmount] = useState('')
  const [payerContactId, setPayerContactId] = useState('')
  const [notes, setNotes] = useState('')
  const [participants, setParticipants] = useState<ParticipantRow[]>([
    { contact_id: '', share_amount: '' },
  ])
  const [error, setError] = useState<string | null>(null)

  const contacts = contactsData?.items ?? []

  const addParticipant = () => {
    setParticipants((prev) => [...prev, { contact_id: '', share_amount: '' }])
  }

  const removeParticipant = (index: number) => {
    setParticipants((prev) => prev.filter((_, i) => i !== index))
  }

  const updateParticipant = (index: number, field: keyof ParticipantRow, value: string) => {
    setParticipants((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p))
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('Vui lòng nhập tiêu đề hóa đơn.')
      return
    }

    const amount = parseFloat(totalAmount)
    if (isNaN(amount) || amount <= 0) {
      setError('Vui lòng nhập tổng tiền hợp lệ.')
      return
    }

    if (!payerContactId) {
      setError('Vui lòng chọn người đã trả tiền.')
      return
    }

    const validParticipants = participants.filter((p) => p.contact_id)
    if (validParticipants.length === 0) {
      setError('Vui lòng thêm ít nhất một người tham gia.')
      return
    }

    const splits: SplitParticipantInput[] = validParticipants.map((p) => ({
      contact_id: p.contact_id,
      share_amount: p.share_amount ? parseFloat(p.share_amount) : 0,
    }))

    const payload: CreateSplitBillPayload = {
      title: title.trim(),
      total_amount: amount,
      payer_contact_id: payerContactId,
      splits,
      notes: notes.trim() || undefined,
    }

    try {
      await createBill.mutateAsync(payload)
      onSuccess?.()
      onClose()
    } catch {
      setError('Có lỗi xảy ra khi tạo hóa đơn. Vui lòng thử lại.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Tạo hóa đơn mới
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tiêu đề <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ví dụ: Bữa tối sinh nhật"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
            />
          </div>

          {/* Total amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tổng tiền (VND) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={totalAmount}
              onChange={(e) => setTotalAmount(e.target.value)}
              placeholder="0"
              min="1"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
            />
          </div>

          {/* Payer */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Người đã trả <span className="text-red-500">*</span>
            </label>
            <select
              value={payerContactId}
              onChange={(e) => setPayerContactId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
            >
              <option value="">-- Chọn liên hệ --</option>
              {contacts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Participants */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Người tham gia <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={addParticipant}
                className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400
                  hover:text-primary-700 dark:hover:text-primary-300 font-medium"
              >
                <Plus className="w-3.5 h-3.5" />
                Thêm người
              </button>
            </div>

            <p className="text-xs text-gray-400 dark:text-gray-500 mb-2">
              Để trống số tiền để chia đều tự động.
            </p>

            <div className="space-y-2">
              {participants.map((participant, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <select
                    value={participant.contact_id}
                    onChange={(e) => updateParticipant(index, 'contact_id', e.target.value)}
                    className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                      bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                      focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                  >
                    <option value="">-- Chọn liên hệ --</option>
                    {contacts.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={participant.share_amount}
                    onChange={(e) => updateParticipant(index, 'share_amount', e.target.value)}
                    placeholder="Tự động"
                    min="0"
                    className="w-28 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                      bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                      focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                  />
                  {participants.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeParticipant(index)}
                      className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20
                        rounded-lg transition-colors flex-shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ghi chú
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Thêm ghi chú (không bắt buộc)"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <Button variant="secondary" type="button" onClick={onClose}>
            Hủy
          </Button>
          <Button
            variant="primary"
            type="submit"
            isLoading={createBill.isPending}
            onClick={handleSubmit}
          >
            Tạo hóa đơn
          </Button>
        </div>
      </div>
    </div>
  )
}

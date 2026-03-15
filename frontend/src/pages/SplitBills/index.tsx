import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button } from '@/components/ui'
import { Plus } from 'lucide-react'

export const SplitBillsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header with Create Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Chia Hóa Đơn
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Quản lý các hóa đơn chia sẻ với bạn bè
          </p>
        </div>
        <Button variant="primary">
          <Plus className="w-5 h-5 mr-2" />
          Tạo Hóa Đơn
        </Button>
      </div>

      {/* Empty State */}
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Chưa có hóa đơn chia sẻ
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Tạo hóa đơn mới để bắt đầu chia sẻ chi phí với bạn bè
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Placeholder Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hóa Đơn Đang Chờ</CardTitle>
            <CardDescription>Những hóa đơn chưa được thanh toán</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 dark:text-gray-400">0 hóa đơn</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hóa Đơn Đã Hoàn Thành</CardTitle>
            <CardDescription>Những hóa đơn đã được thanh toán</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 dark:text-gray-400">0 hóa đơn</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

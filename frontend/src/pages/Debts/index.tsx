import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button } from '@/components/ui'
import { Plus } from 'lucide-react'

export const DebtsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header with Create Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Quản Lý Nợ
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Theo dõi các khoản nợ và lập kế hoạch thanh toán
          </p>
        </div>
        <Button variant="primary">
          <Plus className="w-5 h-5 mr-2" />
          Thêm Nợ
        </Button>
      </div>

      {/* Empty State */}
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-6xl mb-4">💳</div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Chưa có khoản nợ nào
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Thêm khoản nợ để quản lý nợ của bạn
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

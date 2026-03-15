import React, { useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button } from '@/components/ui'
import { Settings, Plus, Trash2 } from 'lucide-react'

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'accounts' | 'categories' | 'rules' | 'parsers' | 'sync' | 'backup'>('accounts')

  const TabButton: React.FC<{
    id: string
    label: string
    active: boolean
    onClick: () => void
  }> = ({ id, label, active, onClick }) => (
    <button
      onClick={onClick}
      className={`px-4 py-2 font-medium border-b-2 transition-colors ${
        active
          ? 'border-primary-600 text-primary-600 dark:text-primary-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Settings className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Cài Đặt
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Quản lý tài khoản, danh mục và cài đặt ứng dụng
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        <TabButton
          id="accounts"
          label="Tài Khoản"
          active={activeTab === 'accounts'}
          onClick={() => setActiveTab('accounts')}
        />
        <TabButton
          id="categories"
          label="Danh Mục"
          active={activeTab === 'categories'}
          onClick={() => setActiveTab('categories')}
        />
        <TabButton
          id="rules"
          label="Quy Tắc"
          active={activeTab === 'rules'}
          onClick={() => setActiveTab('rules')}
        />
        <TabButton
          id="parsers"
          label="Email Parsers"
          active={activeTab === 'parsers'}
          onClick={() => setActiveTab('parsers')}
        />
        <TabButton
          id="sync"
          label="Đồng Bộ Email"
          active={activeTab === 'sync'}
          onClick={() => setActiveTab('sync')}
        />
        <TabButton
          id="backup"
          label="Sao Lưu"
          active={activeTab === 'backup'}
          onClick={() => setActiveTab('backup')}
        />
      </div>

      {/* Content */}
      {activeTab === 'accounts' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Tài Khoản Ngân Hàng
            </h3>
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Thêm Tài Khoản
            </Button>
          </div>
          <Card>
            <CardContent className="flex items-center justify-center h-40">
              <p className="text-gray-500 dark:text-gray-400">
                Không có tài khoản nào được thêm
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'categories' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Danh Mục Chi Tiêu
            </h3>
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Thêm Danh Mục
            </Button>
          </div>
          <Card>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-semibold">Danh Mục</th>
                    <th className="text-left py-3 px-4 font-semibold">Loại</th>
                    <th className="text-right py-3 px-4 font-semibold">Hành Động</th>
                  </tr>
                </thead>
                <tbody>
                  {['Mua sắm', 'Ăn uống', 'Tiện ích', 'Giải trí'].map((cat) => (
                    <tr
                      key={cat}
                      className="border-b border-gray-100 dark:border-gray-800"
                    >
                      <td className="py-3 px-4">{cat}</td>
                      <td className="py-3 px-4">Tùy chỉnh</td>
                      <td className="py-3 px-4 text-right">
                        <button className="text-danger-600 hover:text-danger-700">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'rules' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quy Tắc Tự Động Phân Loại</CardTitle>
            <CardDescription>
              Tạo quy tắc để tự động phân loại giao dịch
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-40">
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Thêm Quy Tắc
            </Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'parsers' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Email Parsers</CardTitle>
            <CardDescription>
              Tạo parser để trích xuất giao dịch từ email
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-40">
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Thêm Parser
            </Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'sync' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Đồng Bộ Email</CardTitle>
            <CardDescription>
              Kết nối email để tự động tải giao dịch
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-40">
            <Button variant="primary">Kết Nối Email</Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'backup' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sao Lưu Dữ Liệu</CardTitle>
              <CardDescription>
                Tải xuống hoặc khôi phục dữ liệu của bạn
              </CardDescription>
            </CardHeader>
            <CardContent className="flex gap-4">
              <Button variant="primary">Sao Lưu Bây Giờ</Button>
              <Button variant="secondary">Khôi Phục Từ File</Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

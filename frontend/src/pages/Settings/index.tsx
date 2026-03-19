import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button } from '@/components/ui'
import { Settings, Plus, Trash2, Mail, Wand2, ChevronRight, Database, FileDown } from 'lucide-react'

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
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Email Parsers
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Link
              to="/settings/email-parsers"
              className="group block"
            >
              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-700">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">
                      Quản lý Email Parsers
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Xem, bật/tắt và kiểm tra các parser
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                </CardContent>
              </Card>
            </Link>

            <Link
              to="/settings/parser-generator"
              className="group block"
            >
              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-700">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                    <Wand2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">
                      Tạo Parser Mới
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Hướng dẫn từng bước từ email mẫu
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                </CardContent>
              </Card>
            </Link>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Thông tin</CardTitle>
              <CardDescription>
                Email parser tự động đọc email ngân hàng và trích xuất giao dịch vào hệ thống.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400 list-disc list-inside">
                <li>Parser có sẵn hỗ trợ hầu hết các ngân hàng Việt Nam lớn</li>
                <li>Tạo custom parser cho ngân hàng chưa được hỗ trợ</li>
                <li>Kiểm tra và debug parser trước khi bật</li>
                <li>Theo dõi tỉ lệ thành công theo thời gian</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'sync' && (
        <div className="space-y-4">
          <Link to="/settings/sync" className="group block">
            <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-700">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                  <Mail className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 dark:text-white text-sm">
                    Quản lý Đồng Bộ Gmail
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Kết nối Gmail, kích hoạt đồng bộ và nhập email thủ công
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
              </CardContent>
            </Card>
          </Link>
        </div>
      )}

      {activeTab === 'backup' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Link to="/settings/backup" className="group block">
              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-700">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="w-10 h-10 rounded-lg bg-success-100 dark:bg-success-900/30 flex items-center justify-center flex-shrink-0">
                    <Database className="w-5 h-5 text-success-600 dark:text-success-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">Sao Lưu & Khôi Phục</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Xuất/nhập toàn bộ dữ liệu JSON</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                </CardContent>
              </Card>
            </Link>

            <Link to="/settings/export" className="group block">
              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-primary-300 dark:hover:border-primary-700">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                    <FileDown className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">Xuất Dữ Liệu</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Xuất CSV/JSON cho Excel, Sheets</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

import React, { useState } from 'react';
import { Download, FileText, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import apiClient, { getCurrentUserId } from '@/api/client';

type ExportFormat = 'csv' | 'json';
type ExportType = 'transactions' | 'categories' | 'accounts';

interface ExportOption {
  type: ExportType;
  label: string;
  formats: ExportFormat[];
  description: string;
}

const EXPORT_OPTIONS: ExportOption[] = [
  {
    type: 'transactions',
    label: 'Giao Dịch',
    formats: ['csv', 'json'],
    description: 'Tất cả giao dịch thu chi với ngày, số tiền, danh mục',
  },
  {
    type: 'categories',
    label: 'Danh Mục',
    formats: ['csv'],
    description: 'Danh sách danh mục chi tiêu',
  },
  {
    type: 'accounts',
    label: 'Tài Khoản',
    formats: ['csv'],
    description: 'Tài khoản ngân hàng và số dư',
  },
];

export const ExportPage: React.FC = () => {
  const [loading, setLoading] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handleExport = async (type: ExportType, format: ExportFormat) => {
    const key = `${type}-${format}`;
    setLoading(key);
    try {
      const params: Record<string, string> = { user_id: getCurrentUserId() };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await apiClient.get(`/export/${type}/${format}`, {
        params,
        responseType: 'blob',
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch
        ? filenameMatch[1]
        : `${type}_${new Date().toISOString().slice(0, 10)}.${format}`;

      const url = URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Xuất dữ liệu thất bại');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Xuất Dữ Liệu</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Xuất dữ liệu tài chính ra CSV hoặc JSON để dùng trong Excel, Google Sheets hoặc phân tích khác
        </p>
      </div>

      {/* Date Range Filter */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Lọc Theo Khoảng Ngày</CardTitle>
          <CardDescription>Áp dụng cho xuất giao dịch. Để trống để xuất tất cả.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Từ ngày
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Đến ngày
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            {(startDate || endDate) && (
              <button
                onClick={() => { setStartDate(''); setEndDate(''); }}
                className="self-end text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Xóa bộ lọc
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Export Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {EXPORT_OPTIONS.map((opt) => (
          <Card key={opt.type}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary-600" />
                {opt.label}
              </CardTitle>
              <CardDescription>{opt.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {opt.formats.map((fmt) => {
                  const key = `${opt.type}-${fmt}`;
                  return (
                    <button
                      key={fmt}
                      onClick={() => handleExport(opt.type, fmt)}
                      disabled={loading === key}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border border-primary-200 dark:border-primary-800 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {loading === key ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5" />
                      )}
                      {fmt.toUpperCase()}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Notes */}
      <Card>
        <CardContent className="py-4">
          <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
            <li>File CSV tương thích với Excel và Google Sheets</li>
            <li>File JSON phù hợp để import vào ứng dụng khác hoặc xử lý bằng code</li>
            <li>Dữ liệu xuất bao gồm tất cả các trường, bao gồm ID nội bộ</li>
            <li>Dữ liệu được lọc theo người dùng hiện tại và khoảng ngày đã chọn</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

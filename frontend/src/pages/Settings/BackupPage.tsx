import React, { useRef, useState } from 'react';
import { Download, Upload, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import apiClient, { getCurrentUserId } from '@/api/client';

export const BackupPage: React.FC = () => {
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreResult, setRestoreResult] = useState<{ stats: Record<string, number>; dry_run: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleExport = async () => {
    setBackupLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/backup/export', {
        params: { user_id: getCurrentUserId() },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance_backup_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Không thể tải xuống backup');
    } finally {
      setBackupLoading(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setRestoreLoading(true);
    setRestoreResult(null);
    setError(null);

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const { data: result } = await apiClient.post('/backup/restore', data, {
        params: { user_id: getCurrentUserId(), dry_run: true },
      });
      setRestoreResult(result.stats);
    } catch {
      setError('File backup không hợp lệ');
    } finally {
      setRestoreLoading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const formatKey = (key: string) =>
    key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Sao Lưu & Khôi Phục</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Tải xuống hoặc khôi phục toàn bộ dữ liệu tài chính của bạn
        </p>
      </div>

      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="w-5 h-5 text-primary-600" />
            Tải Xuống Backup
          </CardTitle>
          <CardDescription>
            Xuất toàn bộ dữ liệu (giao dịch, ngân sách, mục tiêu, v.v.) thành file JSON
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            {['Tài khoản ngân hàng', 'Giao dịch', 'Danh mục', 'Ngân sách', 'Mục tiêu', 'Khoản nợ', 'Subscription', 'Hóa đơn chia sẻ'].map(
              (item) => (
                <div key={item} className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <CheckCircle className="w-4 h-4 text-success-500 flex-shrink-0" />
                  {item}
                </div>
              )
            )}
          </div>
          <button
            onClick={handleExport}
            disabled={backupLoading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {backupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {backupLoading ? 'Đang xuất...' : 'Tải Xuống Backup'}
          </button>
        </CardContent>
      </Card>

      {/* Restore */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="w-5 h-5 text-warning-600" />
            Khôi Phục Từ Backup
          </CardTitle>
          <CardDescription>
            Tải lên file JSON backup để xem trước nội dung (dry run) trước khi khôi phục thực sự
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={restoreLoading}
              className="flex items-center gap-2 px-4 py-2 bg-warning-600 text-white rounded-lg hover:bg-warning-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {restoreLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {restoreLoading ? 'Đang kiểm tra...' : 'Chọn File Backup'}
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-danger-600 dark:text-danger-400 text-sm">
              <XCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {restoreResult && (
            <div className="p-4 rounded-lg bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800">
              <p className="font-medium text-success-700 dark:text-success-300 mb-2">
                Dry Run — Nội dung backup:
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(restoreResult)
                  .filter(([k]) => k !== 'dry_run')
                  .map(([key, count]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">{formatKey(key)}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
              </div>
              <p className="text-xs text-gray-500 mt-3">
                Liên hệ hỗ trợ để thực hiện khôi phục toàn bộ dữ liệu.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

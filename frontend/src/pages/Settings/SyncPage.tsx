import React, { useState } from 'react';
import { RefreshCw, Mail, CheckCircle, XCircle, Loader2, Unlink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { useSyncStore } from '@/store/sync-store';
import apiClient, { getCurrentUserId } from '@/api/client';

interface EmailAccount {
  id: string;
  email: string;
  is_active: boolean;
  last_synced_at: string | null;
}

export const SyncPage: React.FC = () => {
  const { status, lastSyncAt, lastError, syncedCount, setStatus, setSyncResult } = useSyncStore();
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncLog, setSyncLog] = useState<string[]>([]);

  const loadAccounts = async () => {
    try {
      const { data } = await apiClient.get('/oauth/accounts', {
        params: { user_id: getCurrentUserId() },
      });
      setAccounts(data);
    } catch {
      // ignore
    }
  };

  React.useEffect(() => {
    loadAccounts();
  }, []);

  const handleConnectGmail = async () => {
    try {
      const { data } = await apiClient.post('/oauth/authorize', {
        user_id: getCurrentUserId(),
        scopes: ['https://www.googleapis.com/auth/gmail.readonly'],
      });
      window.location.href = data.auth_url;
    } catch (err) {
      console.error('OAuth error', err);
    }
  };

  const handleSync = async (accountId?: string) => {
    setLoading(true);
    setStatus('syncing');
    setSyncLog([]);
    try {
      const { data } = await apiClient.post('/email-sync/trigger', {
        user_id: getCurrentUserId(),
        email_account_id: accountId,
        max_results: 50,
      });
      setSyncResult(data.synced_count ?? 0);
      setSyncLog(data.logs ?? []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Đồng bộ thất bại';
      setSyncResult(0, message);
    } finally {
      setLoading(false);
      loadAccounts();
    }
  };

  const handleDisconnect = async (accountId: string) => {
    if (!confirm('Bạn có chắc muốn ngắt kết nối tài khoản này?')) return;
    try {
      await apiClient.delete(`/oauth/${accountId}`);
      setAccounts((prev) => prev.filter((a) => a.id !== accountId));
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Đồng Bộ Email</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Kết nối Gmail và đồng bộ giao dịch từ email ngân hàng
        </p>
      </div>

      {/* Connect Gmail */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Kết Nối Gmail
          </CardTitle>
          <CardDescription>Thêm tài khoản Gmail để tự động phân tích email giao dịch</CardDescription>
        </CardHeader>
        <CardContent>
          <button
            onClick={handleConnectGmail}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Mail className="w-4 h-4" />
            Kết Nối Gmail Mới
          </button>
        </CardContent>
      </Card>

      {/* Connected Accounts */}
      {accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tài Khoản Đã Kết Nối</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${acc.is_active ? 'bg-success-500' : 'bg-gray-400'}`} />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{acc.email}</p>
                      {acc.last_synced_at && (
                        <p className="text-xs text-gray-500">
                          Đồng bộ lần cuối: {new Date(acc.last_synced_at).toLocaleString('vi-VN')}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSync(acc.id)}
                      disabled={loading}
                      className="p-2 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                      title="Đồng bộ ngay"
                    >
                      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={() => handleDisconnect(acc.id)}
                      className="p-2 text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-lg transition-colors"
                      title="Ngắt kết nối"
                    >
                      <Unlink className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sync All Button */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Đồng Bộ Tất Cả</CardTitle>
          <CardDescription>Kéo email giao dịch từ tất cả tài khoản đã kết nối</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <button
            onClick={() => handleSync()}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            {loading ? 'Đang đồng bộ...' : 'Đồng Bộ Ngay'}
          </button>

          {/* Status */}
          {status === 'success' && (
            <div className="flex items-center gap-2 text-success-600 dark:text-success-400">
              <CheckCircle className="w-5 h-5" />
              <span>Đồng bộ thành công — {syncedCount} giao dịch mới</span>
              {lastSyncAt && (
                <span className="text-xs text-gray-500">
                  lúc {new Date(lastSyncAt).toLocaleTimeString('vi-VN')}
                </span>
              )}
            </div>
          )}
          {status === 'error' && (
            <div className="flex items-center gap-2 text-danger-600 dark:text-danger-400">
              <XCircle className="w-5 h-5" />
              <span>{lastError ?? 'Đồng bộ thất bại'}</span>
            </div>
          )}

          {/* Sync Log */}
          {syncLog.length > 0 && (
            <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg font-mono text-xs text-gray-700 dark:text-gray-300 space-y-1 max-h-40 overflow-y-auto">
              {syncLog.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Manual Email Paste */}
      <ManualEmailIngest />
    </div>
  );
};

const ManualEmailIngest: React.FC = () => {
  const [emailBody, setEmailBody] = useState('');
  const [sender, setSender] = useState('');
  const [subject, setSubject] = useState('');
  const [result, setResult] = useState<{ created: number; errors: string[] } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleIngest = async () => {
    if (!emailBody.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const { data } = await apiClient.post('/ingest/email', {
        email_body: emailBody,
        sender,
        subject,
        account_id: 'default',
        user_id: getCurrentUserId(),
      });
      setResult(data);
    } catch {
      setResult({ created: 0, errors: ['Không thể nhập giao dịch'] });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nhập Email Thủ Công</CardTitle>
        <CardDescription>Dán nội dung email để phân tích và nhập giao dịch</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input
            type="text"
            placeholder="Người gửi (sender)"
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          />
          <input
            type="text"
            placeholder="Tiêu đề (subject)"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          />
        </div>
        <textarea
          rows={6}
          placeholder="Dán nội dung email vào đây..."
          value={emailBody}
          onChange={(e) => setEmailBody(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono resize-none"
        />
        <button
          onClick={handleIngest}
          disabled={loading || !emailBody.trim()}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
          Phân Tích & Nhập
        </button>
        {result && (
          <div className={`p-3 rounded-lg text-sm ${result.errors.length ? 'bg-danger-50 dark:bg-danger-900/20 text-danger-700' : 'bg-success-50 dark:bg-success-900/20 text-success-700'}`}>
            {result.errors.length ? (
              <p>{result.errors.join(', ')}</p>
            ) : (
              <p>Đã nhập {result.created} giao dịch thành công!</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

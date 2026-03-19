import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  Wallet,
  Mail,
  Tag,
  BarChart2,
  Sparkles,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui';

interface Step {
  id: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

const STEPS_COUNT = 5;

export const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [accountName, setAccountName] = useState('');
  const [initialBalance, setInitialBalance] = useState('');
  const [gmailConnected, setGmailConnected] = useState(false);

  const steps: Step[] = [
    {
      id: 0,
      title: 'Chào Mừng!',
      description: 'Hãy thiết lập tài khoản của bạn trong 5 bước đơn giản',
      icon: <Sparkles className="w-8 h-8 text-primary-500" />,
      content: (
        <div className="text-center space-y-4">
          <div className="w-20 h-20 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto">
            <Sparkles className="w-10 h-10 text-primary-600 dark:text-primary-400" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            Chào mừng đến với ứng dụng quản lý tài chính cá nhân!
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            Ứng dụng giúp bạn theo dõi thu chi, phân tích xu hướng, quản lý ngân sách và mục tiêu tiết kiệm.
            Hãy bắt đầu thiết lập ngay!
          </p>
        </div>
      ),
    },
    {
      id: 1,
      title: 'Tạo Tài Khoản',
      description: 'Thêm tài khoản ngân hàng đầu tiên của bạn',
      icon: <Wallet className="w-8 h-8 text-success-500" />,
      content: (
        <div className="space-y-4 max-w-sm mx-auto">
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Nhập thông tin tài khoản ngân hàng chính của bạn để bắt đầu theo dõi.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên Tài Khoản
            </label>
            <input
              type="text"
              placeholder="VD: Cake VPBank"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Số Dư Hiện Tại (VND)
            </label>
            <input
              type="number"
              placeholder="0"
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      ),
    },
    {
      id: 2,
      title: 'Kết Nối Gmail',
      description: 'Đồng bộ giao dịch từ email ngân hàng tự động',
      icon: <Mail className="w-8 h-8 text-primary-500" />,
      content: (
        <div className="space-y-4 max-w-sm mx-auto text-center">
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Kết nối Gmail để ứng dụng tự động đọc và phân tích email giao dịch từ ngân hàng.
            Ứng dụng chỉ đọc email — không bao giờ gửi hay xóa.
          </p>
          {gmailConnected ? (
            <div className="flex items-center justify-center gap-2 text-success-600 dark:text-success-400">
              <CheckCircle className="w-6 h-6" />
              <span className="font-medium">Gmail đã kết nối!</span>
            </div>
          ) : (
            <button
              onClick={() => setGmailConnected(true)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-900 dark:text-white font-medium"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Kết Nối Gmail
            </button>
          )}
          <p className="text-xs text-gray-400">Bạn có thể bỏ qua bước này và kết nối sau</p>
        </div>
      ),
    },
    {
      id: 3,
      title: 'Danh Mục Chi Tiêu',
      description: 'Thiết lập danh mục để phân loại giao dịch',
      icon: <Tag className="w-8 h-8 text-warning-500" />,
      content: (
        <div className="space-y-4 max-w-sm mx-auto">
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Hệ thống đã tự động tạo 27 danh mục phổ biến cho bạn. Bạn có thể tuỳ chỉnh chúng sau trong phần Cài Đặt.
          </p>
          <div className="grid grid-cols-2 gap-2">
            {['Ăn uống', 'Mua sắm', 'Đi lại', 'Giải trí', 'Y tế', 'Giáo dục', 'Tiện ích', 'Lương'].map(
              (cat) => (
                <div
                  key={cat}
                  className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                >
                  <CheckCircle className="w-4 h-4 text-success-500 flex-shrink-0" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{cat}</span>
                </div>
              )
            )}
          </div>
          <p className="text-xs text-gray-500">và 19 danh mục khác...</p>
        </div>
      ),
    },
    {
      id: 4,
      title: 'Tất Cả Sẵn Sàng!',
      description: 'Bạn đã thiết lập xong, bắt đầu theo dõi tài chính ngay!',
      icon: <BarChart2 className="w-8 h-8 text-primary-500" />,
      content: (
        <div className="text-center space-y-4">
          <div className="w-20 h-20 bg-success-100 dark:bg-success-900/30 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-10 h-10 text-success-600 dark:text-success-400" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            Thiết lập hoàn tất!
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            Bạn đã sẵn sàng bắt đầu. Hãy khám phá bảng điều khiển để xem tổng quan tài chính của bạn.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-left mt-4">
            <div className="p-3 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
              <p className="font-medium text-primary-700 dark:text-primary-300">Dashboard</p>
              <p className="text-xs text-gray-500 mt-1">Tổng quan thu-chi hàng tháng</p>
            </div>
            <div className="p-3 rounded-lg bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800">
              <p className="font-medium text-success-700 dark:text-success-300">Giao Dịch</p>
              <p className="text-xs text-gray-500 mt-1">Lịch sử và phân loại</p>
            </div>
            <div className="p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800">
              <p className="font-medium text-warning-700 dark:text-warning-300">Báo Cáo</p>
              <p className="text-xs text-gray-500 mt-1">Xu hướng và phân tích</p>
            </div>
          </div>
        </div>
      ),
    },
  ];

  const isLastStep = currentStep === STEPS_COUNT - 1;
  const step = steps[currentStep];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {steps.map((s, i) => (
            <React.Fragment key={s.id}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  i < currentStep
                    ? 'bg-success-500 text-white'
                    : i === currentStep
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                }`}
              >
                {i < currentStep ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              {i < STEPS_COUNT - 1 && (
                <div
                  className={`h-1 flex-1 max-w-[40px] rounded-full transition-colors ${
                    i < currentStep ? 'bg-success-500' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        <Card>
          <CardContent className="p-8">
            {/* Step Header */}
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">{step.icon}</div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">{step.title}</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{step.description}</p>
            </div>

            {/* Step Content */}
            <div className="mb-8">{step.content}</div>

            {/* Navigation */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
                disabled={currentStep === 0}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Quay lại
              </button>

              {isLastStep ? (
                <button
                  onClick={() => navigate('/')}
                  className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                >
                  Bắt Đầu
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={() => setCurrentStep((s) => Math.min(STEPS_COUNT - 1, s + 1))}
                  className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                >
                  Tiếp Theo
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

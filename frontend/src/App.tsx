import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { AuthProvider } from './store/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import EventsPage from './pages/Events';
import ClientsPage from './pages/Clients';
import StaffPage from './pages/Staff';
import CashierPage from './pages/Cashier';
import DiscountsPage from './pages/Discounts';
import ReportsPage from './pages/Reports';
import AuditPage from './pages/Audit';
import SettingsPage from './pages/Settings';

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/events" element={<ProtectedRoute allowedRoles={['admin', 'manager']}><EventsPage /></ProtectedRoute>} />
              <Route path="/clients" element={<ProtectedRoute allowedRoles={['admin', 'manager']}><ClientsPage /></ProtectedRoute>} />
              <Route path="/staff" element={<ProtectedRoute allowedRoles={['admin']}><StaffPage /></ProtectedRoute>} />
              <Route path="/cashier" element={<ProtectedRoute allowedRoles={['admin', 'manager']}><CashierPage /></ProtectedRoute>} />
              <Route path="/discounts" element={<ProtectedRoute allowedRoles={['admin', 'manager']}><DiscountsPage /></ProtectedRoute>} />
              <Route path="/reports" element={<ProtectedRoute allowedRoles={['admin', 'manager']}><ReportsPage /></ProtectedRoute>} />
              <Route path="/audit" element={<ProtectedRoute allowedRoles={['admin']}><AuditPage /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute allowedRoles={['admin']}><SettingsPage /></ProtectedRoute>} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}

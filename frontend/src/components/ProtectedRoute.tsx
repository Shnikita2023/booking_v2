import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '../store/AuthContext';
import type { RoleCode } from '../types/user';

interface Props {
  children: React.ReactNode;
  allowedRoles?: RoleCode[];
}

export default function ProtectedRoute({ children, allowedRoles }: Props) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user?.role && !allowedRoles.includes(user.role as RoleCode)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

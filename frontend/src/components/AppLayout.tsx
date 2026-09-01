import { useState } from 'react';
import { Layout, Menu, theme, Avatar, Dropdown } from 'antd';
import {
  DashboardOutlined,
  CalendarOutlined,
  UserOutlined,
  TeamOutlined,
  ShopOutlined,
  TagOutlined,
  BarChartOutlined,
  AuditOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import type { RoleCode } from '../types/user';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Главная', roles: ['admin', 'manager', 'cashier'] as RoleCode[] },
  { key: '/events', icon: <CalendarOutlined />, label: 'Мероприятия', roles: ['admin', 'manager'] as RoleCode[] },
  { key: '/clients', icon: <UserOutlined />, label: 'Клиенты', roles: ['admin', 'manager'] as RoleCode[] },
  { key: '/staff', icon: <TeamOutlined />, label: 'Персонал', roles: ['admin'] as RoleCode[] },
  { key: '/cashier', icon: <ShopOutlined />, label: 'Касса', roles: ['admin', 'manager'] as RoleCode[] },
  { key: '/discounts', icon: <TagOutlined />, label: 'Скидки', roles: ['admin', 'manager'] as RoleCode[] },
  { key: '/reports', icon: <BarChartOutlined />, label: 'Отчёты', roles: ['admin', 'manager'] as RoleCode[] },
  { key: '/audit', icon: <AuditOutlined />, label: 'Аудит', roles: ['admin'] as RoleCode[] },
  { key: '/settings', icon: <SettingOutlined />, label: 'Настройки', roles: ['admin'] as RoleCode[] },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();

  const role = user?.role as RoleCode | undefined;
  const filteredItems = menuItems.filter((item) => !role || item.roles.includes(role));

  const userMenuItems = [
    { key: 'role', label: `Роль: ${user?.role ?? '—'}`, disabled: true },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Выйти', onClick: logout },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 32, margin: 16, color: '#fff', fontWeight: 700, fontSize: collapsed ? 14 : 18, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden' }}>
          {collapsed ? 'B' : 'Booking'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={filteredItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: colorBgContainer, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar style={{ backgroundColor: '#1677ff', cursor: 'pointer' }} icon={<UserOutlined />} />
          </Dropdown>
        </Header>
        <Content style={{ margin: 24 }}>
          <div style={{ padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, minHeight: 360 }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

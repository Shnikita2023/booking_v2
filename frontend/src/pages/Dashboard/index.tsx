import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Spin } from 'antd';
import { CalendarOutlined, UserOutlined, ShopOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { events, clients, cashier } from '../../api/endpoints';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({ events: 0, clients: 0, orders: 0 });

  useEffect(() => {
    async function load() {
      try {
        const [ev, cl, or] = await Promise.all([
          events.list(1, 0),
          clients.list(1, 0),
          cashier.list(1, 0),
        ]);
        setCounts({
          events: ev.data.total,
          clients: cl.data.total,
          orders: or.data.total,
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <Spin size="large" />;

  return (
    <>
      <h2>Главная</h2>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card hoverable onClick={() => navigate('/events')} style={{ cursor: 'pointer' }}>
            <Statistic title="Мероприятия" value={counts.events} prefix={<CalendarOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card hoverable onClick={() => navigate('/clients')} style={{ cursor: 'pointer' }}>
            <Statistic title="Клиенты" value={counts.clients} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card hoverable onClick={() => navigate('/cashier')} style={{ cursor: 'pointer' }}>
            <Statistic title="Заказы (всего)" value={counts.orders} prefix={<ShopOutlined />} />
          </Card>
        </Col>
      </Row>
    </>
  );
}

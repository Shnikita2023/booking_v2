import { useEffect, useState } from 'react';
import { Select, Table, Button, Card, Space, Typography, Divider, message, Tag, Modal } from 'antd';
import { ShoppingCartOutlined } from '@ant-design/icons';
import { events, cashier, clients } from '../../api/endpoints';
import type { EventRead, TicketTypeRead } from '../../types/event';
import type { ClientRead } from '../../types/client';
import type { OrderRead } from '../../types/order';

const { Text } = Typography;

export default function CashierPage() {
  const [eventList, setEventList] = useState<EventRead[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<EventRead | null>(null);
  const [ticketTypes, setTicketTypes] = useState<Array<TicketTypeRead & { quantity: number }>>([]);
  const [clientList, setClientList] = useState<ClientRead[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderRead[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    events.list(100, 0).then(({ data }) => setEventList(data.items.filter((e) => e.status === 'on_sale')));
    clients.list(100, 0).then(({ data }) => setClientList(data.items));
    loadRecent();
  }, []);

  const loadRecent = async () => {
    const { data } = await cashier.list(10, 0);
    setRecentOrders(data.items);
  };

  const handleEventChange = async (eventId: string) => {
    const ev = eventList.find((e) => e.id === eventId);
    setSelectedEvent(ev ?? null);
    if (ev) {
      const { data } = await events.listTicketTypes(eventId);
      setTicketTypes(data.items.map((t) => ({ ...t, quantity: 0 })));
    }
  };

  const updateQuantity = (index: number, delta: number) => {
    setTicketTypes((prev) =>
      prev.map((t, i) => (i === index ? { ...t, quantity: Math.max(0, Math.min(t.quota - t.sold, t.quantity + delta)) } : t))
    );
  };

  const total = ticketTypes.reduce((sum, t) => sum + Number(t.price) * t.quantity, 0);
  const selectedClient = clientList.find((c) => c.id === selectedClientId);
  const discount = selectedClient?.discount_percent ?? 0;
  const finalTotal = total * (1 - discount / 100);

  const handleSell = async () => {
    if (!selectedEvent) return;
    const items = ticketTypes.filter((t) => t.quantity > 0).map((t) => ({ ticket_type_id: t.id, quantity: t.quantity }));
    if (items.length === 0) {
      message.warning('Выберите количество билетов');
      return;
    }
    setLoading(true);
    try {
      await cashier.sell({ event_id: selectedEvent.id, items });
      message.success(`Продано! Итого: ${finalTotal.toFixed(2)} ₽`);
      setSelectedEvent(null);
      setTicketTypes([]);
      setSelectedClientId(null);
      loadRecent();
    } catch {
      message.error('Ошибка при продаже');
    } finally {
      setLoading(false);
    }
  };

  const handleRefund = async (orderId: string) => {
    Modal.confirm({
      title: 'Вернуть заказ?',
      onOk: async () => {
        await cashier.refund(orderId);
        message.success('Возврат оформлен');
        loadRecent();
      },
    });
  };

  const handleCancel = async (orderId: string) => {
    Modal.confirm({
      title: 'Отменить заказ?',
      onOk: async () => {
        await cashier.cancel(orderId);
        message.success('Заказ отменён');
        loadRecent();
      },
    });
  };

  const statusColors: Record<string, string> = { reserved: 'orange', paid: 'green', cancelled: 'red', refunded: 'purple' };

  return (
    <>
      <h2>Касса</h2>
      <div style={{ display: 'flex', gap: 24 }}>
        <div style={{ flex: 1 }}>
          <Card title="Новая продажа">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text>Мероприятие:</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="Выберите мероприятие"
                  value={selectedEvent?.id}
                  onChange={handleEventChange}
                  options={eventList.map((e) => ({ value: e.id, label: `${e.title} (${e.venue ?? '—'})` }))}
                />
              </div>
              {ticketTypes.length > 0 && (
                <Table
                  rowKey="id"
                  dataSource={ticketTypes}
                  pagination={false}
                  columns={[
                    { title: 'Тариф', dataIndex: 'name' },
                    { title: 'Цена', dataIndex: 'price', render: (v: string) => `${v} ₽` },
                    { title: 'Свободно', render: (_: unknown, r: TicketTypeRead & { quantity: number }) => r.quota - r.sold },
                    {
                      title: 'Кол-во', render: (_: unknown, r: TicketTypeRead & { quantity: number }) => (
                        <Space>
                          <Button size="small" onClick={() => updateQuantity(ticketTypes.indexOf(r), -1)}>-</Button>
                          <Text strong>{r.quantity}</Text>
                          <Button size="small" onClick={() => updateQuantity(ticketTypes.indexOf(r), 1)}>+</Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              )}
              <Divider />
              <div>
                <Text>Клиент (необязательно):</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="Без клиента"
                  allowClear
                  value={selectedClientId}
                  onChange={setSelectedClientId}
                  options={clientList.map((c) => ({ value: c.id, label: `${c.full_name ?? c.email} (${c.discount_percent}% скидка)` }))}
                />
              </div>
              <Divider />
              <div style={{ textAlign: 'right' }}>
                <Text>Итого: <Text strong style={{ fontSize: 20 }}>{finalTotal.toFixed(2)} ₽</Text></Text>
                {discount > 0 && <Text type="secondary"> (скидка {discount}%)</Text>}
              </div>
              <Button type="primary" size="large" icon={<ShoppingCartOutlined />} loading={loading} onClick={handleSell} block>
                Оформить и оплатить
              </Button>
            </Space>
          </Card>
        </div>
        <div style={{ width: 400 }}>
          <Card title="Последние заказы">
            <Table
              rowKey="id"
              dataSource={recentOrders}
              pagination={false}
              size="small"
              columns={[
                { title: 'ID', dataIndex: 'id', render: (v: string) => v.slice(0, 8) },
                { title: 'Сумма', dataIndex: 'total_amount', render: (v: string) => `${v} ₽` },
                { title: 'Статус', dataIndex: 'status', render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag> },
                {
                  title: '', render: (_: unknown, r: OrderRead) => (
                    <Space size="small">
                      {r.status === 'paid' && <Button size="small" danger onClick={() => handleRefund(r.id)}>Возврат</Button>}
                      {r.status === 'reserved' && <Button size="small" danger onClick={() => handleCancel(r.id)}>Отмена</Button>}
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      </div>
    </>
  );
}

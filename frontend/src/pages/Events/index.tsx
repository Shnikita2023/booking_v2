import { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, DatePicker, InputNumber, Switch, message, Popconfirm, Drawer } from 'antd';
import { PlusOutlined, EditOutlined, CopyOutlined, PlayCircleOutlined, PauseCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { events } from '../../api/endpoints';
import type { EventRead, EventStatus, TicketTypeRead, TicketTypeCreate } from '../../types/event';
import dayjs from 'dayjs';

const statusColors: Record<EventStatus, string> = {
  draft: 'default',
  on_sale: 'success',
  paused: 'warning',
  cancelled: 'error',
  completed: 'processing',
  moved: 'purple',
};

const statusLabels: Record<EventStatus, string> = {
  draft: 'Черновик',
  on_sale: 'В продаже',
  paused: 'Приостановлен',
  cancelled: 'Отменён',
  completed: 'Завершён',
  moved: 'Перенесён',
};

export default function EventsPage() {
  const [items, setItems] = useState<EventRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<EventRead | null>(null);
  const [ttDrawer, setTtDrawer] = useState<EventRead | null>(null);
  const [ticketTypes, setTicketTypes] = useState<TicketTypeRead[]>([]);
  const [ttFormOpen, setTtFormOpen] = useState(false);
  const [editingTt, setEditingTt] = useState<TicketTypeRead | null>(null);
  const [form] = Form.useForm();
  const [ttForm] = Form.useForm();
  const limit = 20;

  const load = async (off = offset) => {
    setLoading(true);
    try {
      const { data } = await events.list(limit, off);
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, []);

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    setFormOpen(true);
  };

  const handleEdit = (record: EventRead) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      starts_at: dayjs(record.starts_at),
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        starts_at: values.starts_at.toISOString(),
        ticket_types: values.ticket_types?.map((t: TicketTypeCreate) => ({ name: t.name, price: t.price, quota: t.quota })),
      };
      if (editing) {
        await events.update(editing.id, payload);
        message.success('Мероприятие обновлено');
      } else {
        await events.create(payload);
        message.success('Мероприятие создано');
      }
      setFormOpen(false);
      load();
    } catch { /* validation error */ }
  };

  const handleAction = async (id: string, action: 'publish' | 'cancel' | 'complete' | 'pause-sales' | 'resume-sales' | 'clone') => {
    try {
      if (action === 'clone') {
        await events.clone(id);
        message.success('Мероприятие клонировано');
      } else if (action === 'publish') {
        await events.publish(id);
        message.success('Опубликовано');
      } else if (action === 'cancel') {
        await events.cancel(id);
        message.success('Отменено');
      } else if (action === 'complete') {
        await events.complete(id);
        message.success('Завершено');
      } else if (action === 'pause-sales') {
        await events.pauseSales(id);
        message.success('Продажи приостановлены');
      } else if (action === 'resume-sales') {
        await events.resumeSales(id);
        message.success('Продажи возобновлены');
      }
      load();
    } catch {
      message.error('Ошибка');
    }
  };

  const loadTicketTypes = async (event: EventRead) => {
    setTtDrawer(event);
    const { data } = await events.listTicketTypes(event.id);
    setTicketTypes(data.items);
  };

  const handleSaveTt = async () => {
    try {
      const values = await ttForm.validateFields();
      if (!ttDrawer) return;
      if (editingTt) {
        await events.updateTicketType(ttDrawer.id, editingTt.id, values);
        message.success('Тариф обновлён');
      } else {
        await events.createTicketType(ttDrawer.id, values);
        message.success('Тариф создан');
      }
      setTtFormOpen(false);
      setEditingTt(null);
      const { data } = await events.listTicketTypes(ttDrawer.id);
      setTicketTypes(data.items);
    } catch { /* validation error */ }
  };

  const handleDeleteTt = async (eventId: string, ttId: string) => {
    await events.deleteTicketType(eventId, ttId);
    message.success('Тариф удалён');
    const { data } = await events.listTicketTypes(eventId);
    setTicketTypes(data.items);
  };

  const columns = [
    { title: 'Название', dataIndex: 'title', key: 'title', width: 200 },
    { title: 'Дата', dataIndex: 'starts_at', key: 'starts_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm') },
    { title: 'Статус', dataIndex: 'status', key: 'status', render: (s: EventStatus) => <Tag color={statusColors[s]}>{statusLabels[s]}</Tag> },
    { title: 'Цена от', dataIndex: 'price', key: 'price', render: (v: string | null) => v ? `${v} ₽` : '—' },
    { title: 'Место', dataIndex: 'venue', key: 'venue' },
    {
      title: 'Действия', key: 'actions', render: (_: unknown, record: EventRead) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Button size="small" onClick={() => loadTicketTypes(record)}>Тарифы</Button>
          {record.status === 'draft' && <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleAction(record.id, 'publish')} />}
          {record.status === 'on_sale' && <Button size="small" icon={<PauseCircleOutlined />} onClick={() => handleAction(record.id, 'pause-sales')} />}
          {record.status === 'paused' && <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleAction(record.id, 'resume-sales')} />}
          {record.status === 'on_sale' && <Button size="small" icon={<CheckCircleOutlined />} onClick={() => handleAction(record.id, 'complete')} />}
          {!['cancelled', 'completed'].includes(record.status) && (
            <Popconfirm title="Отменить мероприятие?" onConfirm={() => handleAction(record.id, 'cancel')}>
              <Button size="small" danger icon={<CloseCircleOutlined />} />
            </Popconfirm>
          )}
          <Button size="small" icon={<CopyOutlined />} onClick={() => handleAction(record.id, 'clone')} />
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Мероприятия</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>Создать</Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ total, pageSize: limit, current: Math.floor(offset / limit) + 1, onChange: (p) => { setOffset((p - 1) * limit); load((p - 1) * limit); } }}
      />

      <Modal title={editing ? 'Редактировать мероприятие' : 'Новое мероприятие'} open={formOpen} onOk={handleSave} onCancel={() => setFormOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="starts_at" label="Дата и время" rules={[{ required: true }]}>
            <DatePicker showTime format="DD.MM.YYYY HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="duration_min" label="Длительность (мин)">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="venue" label="Место">
            <Input />
          </Form.Item>
          <Form.Item name="age_rating" label="Возраст">
            <Input />
          </Form.Item>
          <Form.Item name="show_free_tickets" label="Показать свободные билеты" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title={`Тарифы: ${ttDrawer?.title ?? ''}`} open={!!ttDrawer} onClose={() => setTtDrawer(null)} width={600}>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => { setEditingTt(null); ttForm.resetFields(); setTtFormOpen(true); }}>
          Добавить тариф
        </Button>
        <Table
          rowKey="id"
          dataSource={ticketTypes}
          columns={[
            { title: 'Название', dataIndex: 'name' },
            { title: 'Цена', dataIndex: 'price', render: (v: string) => `${v} ₽` },
            { title: 'Квота', dataIndex: 'quota' },
            { title: 'Продано', dataIndex: 'sold' },
            {
              title: 'Действия', render: (_: unknown, r: TicketTypeRead) => (
                <Space>
                  <Button size="small" onClick={() => { setEditingTt(r); ttForm.setFieldsValue(r); setTtFormOpen(true); }}>Edit</Button>
                  <Popconfirm title="Удалить?" onConfirm={() => ttDrawer && handleDeleteTt(ttDrawer.id, r.id)}>
                    <Button size="small" danger>Delete</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
        <Modal title={editingTt ? 'Редактировать тариф' : 'Новый тариф'} open={ttFormOpen} onOk={handleSaveTt} onCancel={() => setTtFormOpen(false)}>
          <Form form={ttForm} layout="vertical">
            <Form.Item name="name" label="Название" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="price" label="Цена" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="quota" label="Квота" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Form>
        </Modal>
      </Drawer>
    </>
  );
}

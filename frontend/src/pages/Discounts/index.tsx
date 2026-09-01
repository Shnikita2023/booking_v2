import { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, InputNumber, Select, Switch, DatePicker, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { discounts } from '../../api/endpoints';
import type { DiscountRead, DiscountType } from '../../types/discount';
import dayjs from 'dayjs';

const typeLabels: Record<DiscountType, string> = { global: 'Глобальная', event: 'Мероприятие', client: 'Клиент' };

export default function DiscountsPage() {
  const [items, setItems] = useState<DiscountRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<DiscountRead | null>(null);
  const [form] = Form.useForm();
  const limit = 20;

  const load = async (off = offset) => {
    setLoading(true);
    try {
      const { data } = await discounts.list(limit, off);
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, []);

  const handleCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ is_active: true, discount_type: 'global' }); setFormOpen(true); };

  const handleEdit = (r: DiscountRead) => {
    setEditing(r);
    form.setFieldsValue({
      ...r,
      valid_from: r.valid_from ? dayjs(r.valid_from) : null,
      valid_until: r.valid_until ? dayjs(r.valid_until) : null,
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        valid_from: values.valid_from?.toISOString() ?? null,
        valid_until: values.valid_until?.toISOString() ?? null,
      };
      if (editing) {
        await discounts.update(editing.id, payload);
        message.success('Скидка обновлена');
      } else {
        await discounts.create(payload);
        message.success('Скидка создана');
      }
      setFormOpen(false);
      load();
    } catch { /* validation */ }
  };

  const handleDelete = async (id: string) => { await discounts.delete(id); message.success('Скидка удалена'); load(); };

  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Скидка', dataIndex: 'percent', key: 'percent', render: (v: number) => `${v}%` },
    { title: 'Тип', dataIndex: 'discount_type', key: 'discount_type', render: (v: DiscountType) => <Tag>{typeLabels[v]}</Tag> },
    { title: 'Активна', dataIndex: 'is_active', key: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Да' : 'Нет'}</Tag> },
    { title: 'Действует с', dataIndex: 'valid_from', key: 'valid_from', render: (v: string | null) => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
    { title: 'Действует до', dataIndex: 'valid_until', key: 'valid_until', render: (v: string | null) => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
    {
      title: 'Действия', render: (_: unknown, r: DiscountRead) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          <Popconfirm title="Удалить скидку?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Скидки</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>Создать</Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ total, pageSize: limit, current: Math.floor(offset / limit) + 1, onChange: (p) => { setOffset((p - 1) * limit); load((p - 1) * limit); } }}
      />
      <Modal title={editing ? 'Редактировать скидку' : 'Новая скидка'} open={formOpen} onOk={handleSave} onCancel={() => setFormOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="percent" label="Процент скидки" rules={[{ required: true }]}>
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="discount_type" label="Тип" rules={[{ required: true }]}>
            <Select options={Object.entries(typeLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="valid_from" label="Действует с">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="valid_until" label="Действует до">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

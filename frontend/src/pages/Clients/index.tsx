import { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, InputNumber, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import { clients } from '../../api/endpoints';
import type { ClientRead } from '../../types/client';
import dayjs from 'dayjs';

export default function ClientsPage() {
  const [items, setItems] = useState<ClientRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ClientRead | null>(null);
  const [form] = Form.useForm();
  const limit = 20;

  const load = async (off = offset) => {
    setLoading(true);
    try {
      const { data } = await clients.list(limit, off);
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, []);

  const handleCreate = () => { setEditing(null); form.resetFields(); setFormOpen(true); };

  const handleEdit = (r: ClientRead) => {
    setEditing(r);
    form.setFieldsValue(r);
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await clients.update(editing.id, values);
        message.success('Клиент обновлён');
      } else {
        await clients.create(values);
        message.success('Клиент создан');
      }
      setFormOpen(false);
      load();
    } catch { /* validation */ }
  };

  const handleBlock = async (id: string) => { await clients.block(id); message.success('Заблокирован'); load(); };
  const handleUnblock = async (id: string) => { await clients.unblock(id); message.success('Разблокирован'); load(); };
  const handleDelete = async (id: string) => { await clients.delete(id); message.success('Удалён'); load(); };

  const columns = [
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Имя', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Телефон', dataIndex: 'phone', key: 'phone' },
    { title: 'Скидка', dataIndex: 'discount_percent', key: 'discount_percent', render: (v: number) => `${v}%` },
    { title: 'Статус', dataIndex: 'is_active', key: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Активен' : 'Заблокирован'}</Tag> },
    { title: 'Создан', dataIndex: 'created_at', key: 'created_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
    {
      title: 'Действия', render: (_: unknown, r: ClientRead) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          {r.is_active ? (
            <Button size="small" danger icon={<StopOutlined />} onClick={() => handleBlock(r.id)} />
          ) : (
            <Button size="small" icon={<CheckCircleOutlined />} onClick={() => handleUnblock(r.id)} />
          )}
          <Popconfirm title="Удалить клиента?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Клиенты</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>Создать</Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ total, pageSize: limit, current: Math.floor(offset / limit) + 1, onChange: (p) => { setOffset((p - 1) * limit); load((p - 1) * limit); } }}
      />
      <Modal title={editing ? 'Редактировать клиента' : 'Новый клиент'} open={formOpen} onOk={handleSave} onCancel={() => setFormOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          {!editing && (
            <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 8 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="full_name" label="Имя">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Телефон">
            <Input />
          </Form.Item>
          <Form.Item name="discount_percent" label="Скидка (%)" initialValue={0}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

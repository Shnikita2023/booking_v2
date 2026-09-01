import { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import { staffUsers } from '../../api/endpoints';
import type { UserRead, RoleCode } from '../../types/user';
import dayjs from 'dayjs';

const roleLabels: Record<RoleCode, string> = { admin: 'Администратор', manager: 'Менеджер', cashier: 'Кассир' };
const roleColors: Record<RoleCode, string> = { admin: 'red', manager: 'blue', cashier: 'green' };

export default function StaffPage() {
  const [items, setItems] = useState<UserRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<UserRead | null>(null);
  const [form] = Form.useForm();
  const limit = 20;

  const load = async (off = offset) => {
    setLoading(true);
    try {
      const { data } = await staffUsers.list(limit, off);
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, []);

  const handleCreate = () => { setEditing(null); form.resetFields(); setFormOpen(true); };

  const handleEdit = (r: UserRead) => {
    setEditing(r);
    form.setFieldsValue(r);
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await staffUsers.update(editing.id, values);
        message.success('Сотрудник обновлён');
      } else {
        await staffUsers.create(values);
        message.success('Сотрудник создан');
      }
      setFormOpen(false);
      load();
    } catch { /* validation */ }
  };

  const handleBlock = async (id: string) => { await staffUsers.block(id); message.success('Заблокирован'); load(); };
  const handleUnblock = async (id: string) => { await staffUsers.unblock(id); message.success('Разблокирован'); load(); };
  const handleDelete = async (id: string) => { await staffUsers.delete(id); message.success('Удалён'); load(); };

  const columns = [
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Имя', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Роль', dataIndex: 'role_code', key: 'role_code', render: (v: RoleCode) => <Tag color={roleColors[v]}>{roleLabels[v]}</Tag> },
    { title: 'Статус', dataIndex: 'is_active', key: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Активен' : 'Заблокирован'}</Tag> },
    { title: 'Создан', dataIndex: 'created_at', key: 'created_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
    {
      title: 'Действия', render: (_: unknown, r: UserRead) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          {r.is_active ? (
            <Button size="small" danger icon={<StopOutlined />} onClick={() => handleBlock(r.id)} />
          ) : (
            <Button size="small" icon={<CheckCircleOutlined />} onClick={() => handleUnblock(r.id)} />
          )}
          <Popconfirm title="Удалить сотрудника?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Персонал</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>Создать</Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ total, pageSize: limit, current: Math.floor(offset / limit) + 1, onChange: (p) => { setOffset((p - 1) * limit); load((p - 1) * limit); } }}
      />
      <Modal title={editing ? 'Редактировать сотрудника' : 'Новый сотрудник'} open={formOpen} onOk={handleSave} onCancel={() => setFormOpen(false)}>
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
          <Form.Item name="role_code" label="Роль" rules={[{ required: true }]}>
            <Select options={Object.entries(roleLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

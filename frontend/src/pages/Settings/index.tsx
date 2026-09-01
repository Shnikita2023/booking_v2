import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, message } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { settings } from '../../api/endpoints';
import type { SettingRead } from '../../types/settings';

export default function SettingsPage() {
  const [items, setItems] = useState<SettingRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<SettingRead | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await settings.list();
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleEdit = (r: SettingRead) => {
    setEditing(r);
    form.setFieldsValue({ value: JSON.stringify(r.value, null, 2), description: r.description });
    setEditOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const parsed = JSON.parse(values.value);
      if (!editing) return;
      await settings.set(editing.key, { value: parsed, description: values.description });
      message.success('Настройка сохранена');
      setEditOpen(false);
      load();
    } catch {
      message.error('Некорректный JSON');
    }
  };

  const columns = [
    { title: 'Ключ', dataIndex: 'key', key: 'key' },
    { title: 'Значение', dataIndex: 'value', key: 'value', render: (v: unknown) => JSON.stringify(v) },
    { title: 'Описание', dataIndex: 'description', key: 'description' },
    { title: 'Обновлено', dataIndex: 'updated_at', key: 'updated_at' },
    {
      title: 'Действия', render: (_: unknown, r: SettingRead) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
      ),
    },
  ];

  return (
    <>
      <h2>Настройки</h2>
      <Table rowKey="key" columns={columns} dataSource={items} loading={loading} pagination={false} />
      <Modal title="Редактировать настройку" open={editOpen} onOk={handleSave} onCancel={() => setEditOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item label="Ключ">
            <Input value={editing?.key} disabled />
          </Form.Item>
          <Form.Item name="value" label="Значение (JSON)" rules={[{ required: true }]}>
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

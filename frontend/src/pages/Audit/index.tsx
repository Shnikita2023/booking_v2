import { useEffect, useState } from 'react';
import { Table, Form, Input, DatePicker, Button } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { audit } from '../../api/endpoints';
import type { AuditRead } from '../../types/audit';
import dayjs from 'dayjs';

export default function AuditPage() {
  const [items, setItems] = useState<AuditRead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [form] = Form.useForm();
  const limit = 20;

  const load = async (off = offset, f = filters) => {
    setLoading(true);
    try {
      const params: Record<string, string | number | undefined> = { limit, offset: off };
      if (f.action) params.action = f.action;
      if (f.actor_type) params.actor_type = f.actor_type;
      if (f.entity_type) params.entity_type = f.entity_type;
      if (f.from_at) params.from_at = f.from_at;
      if (f.to_at) params.to_at = f.to_at;
      const { data } = await audit.list(params);
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, []);

  const handleSearch = () => {
    const values = form.getFieldsValue();
    const f: Record<string, string | undefined> = {
      action: values.action,
      actor_type: values.actor_type,
      entity_type: values.entity_type,
      from_at: values.dates?.[0]?.toISOString(),
      to_at: values.dates?.[1]?.toISOString(),
    };
    setFilters(f);
    setOffset(0);
    load(0, f);
  };

  const columns = [
    { title: 'Время', dataIndex: 'created_at', key: 'created_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm:ss') },
    { title: 'Действие', dataIndex: 'action', key: 'action' },
    { title: 'Актор', dataIndex: 'actor_id', key: 'actor_id', render: (v: string | null) => v?.slice(0, 8) ?? '—' },
    { title: 'Роль', dataIndex: 'actor_role', key: 'actor_role' },
    { title: 'Тип объекта', dataIndex: 'entity_type', key: 'entity_type' },
    { title: 'ID объекта', dataIndex: 'entity_id', key: 'entity_id', render: (v: string | null) => v?.slice(0, 8) ?? '—' },
  ];

  return (
    <>
      <h2>Журнал аудита</h2>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="action"><Input placeholder="Действие" allowClear /></Form.Item>
        <Form.Item name="actor_type"><Input placeholder="Тип актора" allowClear /></Form.Item>
        <Form.Item name="entity_type"><Input placeholder="Тип объекта" allowClear /></Form.Item>
        <Form.Item name="dates"><DatePicker.RangePicker /></Form.Item>
        <Form.Item><Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>Поиск</Button></Form.Item>
      </Form>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ total, pageSize: limit, current: Math.floor(offset / limit) + 1, onChange: (p) => { setOffset((p - 1) * limit); load((p - 1) * limit); } }}
      />
    </>
  );
}

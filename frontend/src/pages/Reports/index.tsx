import { useState } from 'react';
import { Tabs, Table, DatePicker, Spin } from 'antd';
import { reports } from '../../api/endpoints';
import type { RevenueReport, RevenueByDateReport, SalesReport, OccupancyReport, TopClientReport, AuditStatsReport } from '../../types/report';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

export default function ReportsPage() {
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);

  const getDateParams = () => ({
    fromDate: dateRange[0]?.toISOString(),
    toDate: dateRange[1]?.toISOString(),
  });

  const withLoading = async <T,>(fn: () => Promise<T>): Promise<T> => {
    setLoading(true);
    try {
      return await fn();
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'revenue',
      label: 'Выручка по мероприятиям',
      children: (
        <ReportTable<RevenueReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.revenue(getDateParams().fromDate, getDateParams().toDate))}
          columns={[
            { title: 'Мероприятие', dataIndex: 'event_title' },
            { title: 'Дата', dataIndex: 'event_starts_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm') },
            { title: 'Выручка', dataIndex: 'total_revenue', render: (v: string) => `${v} ₽` },
            { title: 'Платежей', dataIndex: 'payment_count' },
          ]}
        />
      ),
    },
    {
      key: 'revenueByDate',
      label: 'Выручка по дням',
      children: (
        <ReportTable<RevenueByDateReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.revenueByDate(getDateParams().fromDate, getDateParams().toDate))}
          columns={[
            { title: 'Дата', dataIndex: 'date', render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
            { title: 'Выручка', dataIndex: 'total_revenue', render: (v: string) => `${v} ₽` },
            { title: 'Платежей', dataIndex: 'payment_count' },
          ]}
        />
      ),
    },
    {
      key: 'sales',
      label: 'Продажи',
      children: (
        <ReportTable<SalesReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.sales(getDateParams().fromDate, getDateParams().toDate))}
          columns={[
            { title: 'Статус', dataIndex: 'status' },
            { title: 'Заказов', dataIndex: 'order_count' },
            { title: 'Сумма', dataIndex: 'total_amount', render: (v: string) => `${v} ₽` },
          ]}
        />
      ),
    },
    {
      key: 'occupancy',
      label: 'Загрузка',
      children: (
        <ReportTable<OccupancyReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.occupancy())}
          columns={[
            { title: 'Мероприятие', dataIndex: 'event_title' },
            { title: 'Дата', dataIndex: 'event_starts_at', render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
            { title: 'Квота', dataIndex: 'total_quota' },
            { title: 'Продано', dataIndex: 'total_sold' },
            { title: 'Загрузка', dataIndex: 'occupancy_pct', render: (v: string) => `${v}%` },
          ]}
        />
      ),
    },
    {
      key: 'topClients',
      label: 'Топ клиентов',
      children: (
        <ReportTable<TopClientReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.topClients())}
          columns={[
            { title: 'Имя', dataIndex: 'full_name' },
            { title: 'Email', dataIndex: 'email' },
            { title: 'Заказов', dataIndex: 'total_orders' },
            { title: 'Потрачено', dataIndex: 'total_spent', render: (v: string) => `${v} ₽` },
          ]}
        />
      ),
    },
    {
      key: 'auditStats',
      label: 'Аудит',
      children: (
        <ReportTable<AuditStatsReport>
          loading={loading}
          onLoad={() => withLoading(() => reports.auditStats(getDateParams().fromDate, getDateParams().toDate))}
          columns={[
            { title: 'Действие', dataIndex: 'action' },
            { title: 'Роль', dataIndex: 'actor_role' },
            { title: 'Количество', dataIndex: 'count' },
          ]}
        />
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Отчёты</h2>
        <RangePicker onChange={(d) => setDateRange(d as [dayjs.Dayjs | null, dayjs.Dayjs | null])} />
      </div>
      {loading && <Spin style={{ display: 'block', margin: '20px auto' }} />}
      <Tabs items={tabItems} />
    </>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ReportTable<T extends Record<string, any>>({ loading, onLoad, columns }: {
  loading: boolean;
  onLoad: () => Promise<{ data: T[] }>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: Array<{ title: string; dataIndex?: string; key?: string; render?: (value: any, record: T) => React.ReactNode }>;
}) {
  const [data, setData] = useState<T[]>([]);
  const [loaded, setLoaded] = useState(false);

  if (!loaded) {
    onLoad().then(({ data }) => { setData(data); setLoaded(true); });
    return <Spin />;
  }

  return <Table rowKey={(_, i) => String(i)} dataSource={data} columns={columns} loading={loading} pagination={false} />;
}

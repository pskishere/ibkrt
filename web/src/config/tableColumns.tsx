/**
 * 表格列配置
 */
import { Button, Tag } from 'antd';
import { CloseCircleOutlined } from '@ant-design/icons';
import type { Order } from '../types/index';
import { statusMaps } from '../utils/formatters';

/**
 * 持仓表格列定义
 */
export const getPositionColumns = () => [
  {
    title: '代码',
    dataIndex: 'symbol',
    key: 'symbol',
    render: (text: string) => <strong>{text}</strong>,
  },
  {
    title: '数量',
    dataIndex: 'position',
    key: 'position',
    render: (value: number | undefined) => value?.toFixed(0) || 0,
  },
  {
    title: '市价',
    dataIndex: 'marketPrice',
    key: 'marketPrice',
    render: (value: number | undefined) => `$${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '市值',
    dataIndex: 'marketValue',
    key: 'marketValue',
    render: (value: number | undefined) => `$${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '成本',
    dataIndex: 'averageCost',
    key: 'averageCost',
    render: (value: number | undefined) => `$${value?.toFixed(2) || '0.00'}`,
  },
  {
    title: '盈亏',
    dataIndex: 'unrealizedPNL',
    key: 'unrealizedPNL',
    render: (value: number | undefined) => {
      const pnl = value || 0;
      return (
        <Tag color={pnl >= 0 ? 'success' : 'error'}>
          ${pnl.toFixed(2)}
        </Tag>
      );
    },
  },
];

/**
 * 订单表格列定义
 */
export const getOrderColumns = (handleCancelOrder: (orderId: number) => void) => [
  {
    title: '订单ID',
    dataIndex: 'orderId',
    key: 'orderId',
    render: (id: number) => `#${id}`,
  },
  {
    title: '代码',
    dataIndex: 'symbol',
    key: 'symbol',
  },
  {
    title: '方向',
    dataIndex: 'action',
    key: 'action',
    render: (action: string) => (
      <Tag color={action === 'BUY' ? 'green' : 'red'}>
        {action === 'BUY' ? '买入' : '卖出'}
      </Tag>
    ),
  },
  {
    title: '数量',
    dataIndex: 'totalQuantity',
    key: 'totalQuantity',
    render: (qty: number | undefined) => qty?.toFixed(0) || 0,
  },
  {
    title: '类型',
    dataIndex: 'orderType',
    key: 'orderType',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (status: string) => {
      const config = statusMaps.order[status as keyof typeof statusMaps.order] || 
        { color: 'default', text: status };
      return <Tag color={config.color}>{config.text}</Tag>;
    },
  },
  {
    title: '已成交',
    dataIndex: 'filled',
    key: 'filled',
    render: (filled: number | undefined) => filled?.toFixed(0) || 0,
  },
  {
    title: '操作',
    key: 'action',
    render: (_: any, record: Order) => (
      record.status !== 'Filled' && record.status !== 'Cancelled' ? (
        <Button
          type="link"
          danger
          icon={<CloseCircleOutlined />}
          onClick={() => handleCancelOrder(record.order_id)}
        >
          撤销
        </Button>
      ) : null
    ),
  },
];

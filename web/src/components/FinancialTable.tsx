/**
 * 财务报表表格组件
 */
import React from 'react';
import { Table } from 'antd';

interface FinancialTableProps {
  data: any[];
}

/**
 * 渲染财务数据
 */
const renderFinancialValue = (value: any): string => {
  if (value === null || value === undefined || value === '') return '-';
  const num = parseFloat(value);
  if (!isNaN(num)) {
    if (Math.abs(num) >= 1e9) {
      return `$${(num / 1e9).toFixed(2)}B`;
    } else if (Math.abs(num) >= 1e6) {
      return `$${(num / 1e6).toFixed(2)}M`;
    }
    return `$${num.toFixed(2)}`;
  }
  return value;
};

/**
 * 生成表格列配置
 */
const getColumns = (firstRecord: any) => {
  const dateCol = firstRecord.index || firstRecord.Date ? {
    title: '日期',
    dataIndex: firstRecord.index ? 'index' : 'Date',
    key: 'date',
    width: 120,
    fixed: 'left' as const,
  } : null;

  const otherCols = Object.keys(firstRecord)
    .filter(key => key !== 'index' && key !== 'Date')
    .map(key => ({
      title: key,
      dataIndex: key,
      key: key,
      render: renderFinancialValue,
    }));

  return dateCol ? [dateCol, ...otherCols] : otherCols;
};

/**
 * 财务报表表格组件
 */
export const FinancialTable: React.FC<FinancialTableProps> = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return null;
  }

  const dataSource = data.map((record: any, index: number) => ({
    key: index,
    ...record,
  }));

  return (
    <Table
      size="small"
      bordered
      dataSource={dataSource}
      columns={getColumns(data[0])}
      scroll={{ x: 'max-content' }}
      pagination={false}
    />
  );
};

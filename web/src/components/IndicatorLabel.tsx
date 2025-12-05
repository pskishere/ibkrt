/**
 * 带知识讲解的指标标签组件
 */
import React from 'react';
import { Space, Popover, Typography } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import type { IndicatorInfo } from '../types/index';

const { Text, Title } = Typography;

interface IndicatorLabelProps {
  label: string;
  indicatorKey: string;
  indicatorInfoMap: Record<string, IndicatorInfo>;
}

/**
 * 创建指标知识讲解的Popover内容
 */
const createKnowledgeContent = (info: IndicatorInfo): React.ReactNode => {
  return (
    <div style={{ maxWidth: 400, fontSize: 13, paddingTop: 0 }}>
      <Title level={5} style={{ marginTop: 0, marginBottom: 0, fontSize: 14 }}>
        {info.name}
      </Title>
      <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
        <strong>说明：</strong>{info.description}
      </Text>
      {info.calculation && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>计算方法：</strong>{info.calculation}
        </Text>
      )}
      {info.reference_range && Object.keys(info.reference_range).length > 0 && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>参考范围：</strong>
          <ul style={{ marginTop: 4, marginBottom: 0, paddingLeft: 20 }}>
            {Object.entries(info.reference_range).map(([key, value]) => (
              <li key={key} style={{ marginBottom: 4 }}>{value}</li>
            ))}
          </ul>
        </Text>
      )}
      {info.interpretation && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>解读：</strong>{info.interpretation}
        </Text>
      )}
      {info.usage && (
        <Text style={{ display: 'block', marginTop: 8, marginBottom: 0 }}>
          <strong>使用方法：</strong>{info.usage}
        </Text>
      )}
    </div>
  );
};

/**
 * 指标标签组件
 */
export const IndicatorLabel: React.FC<IndicatorLabelProps> = ({ label, indicatorKey, indicatorInfoMap }) => {
  const info = indicatorInfoMap[indicatorKey];
  
  if (!info) {
    return <span>{label}</span>;
  }

  return (
    <Space>
      <span>{label}</span>
      <Popover
        content={createKnowledgeContent(info)}
        title={null}
        trigger="click"
        placement="right"
        styles={{ body: { paddingTop: 8, paddingBottom: 12 } }}
      >
        <QuestionCircleOutlined
          style={{
            color: '#1890ff',
            cursor: 'pointer',
            fontSize: 12,
          }}
        />
      </Popover>
    </Space>
  );
};

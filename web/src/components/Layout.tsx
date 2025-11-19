/**
 * 布局组件 - 无顶栏，直接显示内容
 */
import React, { type ReactNode } from 'react';
import { Layout as AntLayout } from 'antd';
import './Layout.css';

const { Content } = AntLayout;

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <AntLayout className="app-layout">
      <Content className="app-content">
        {children}
      </Content>
    </AntLayout>
  );
};

export default Layout;


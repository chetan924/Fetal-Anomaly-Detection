import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import Header from './Header';
import Sidebar from './Sidebar';

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onToggle={() =>
          setSidebarCollapsed((value) => !value)
        }
      />

      <div
        className={`min-h-screen transition-all duration-200 ${
          sidebarCollapsed
            ? 'lg:pl-24'
            : 'lg:pl-72'
        }`}
      >
        <Header
          title="FetalAI Workspace"
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;

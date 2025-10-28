import React, { useState } from 'react';
import AppHeader from './AppHeader';
import Sidebar from './Sidebar';
import styles from './Layout.module.css'; // This will be our new CSS file

export default function Layout({ children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  return (
    // This class name comes from the *new* Layout.module.css
    <div className={styles.layoutContainer}>
      <AppHeader onToggleSidebar={toggleSidebar} />
      
      <main className={styles.content}>
        {children}
      </main>
      
      <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />
    </div>
  );
}
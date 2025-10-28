import React from 'react';
import { Link } from 'react-router-dom';
import styles from './AppHeader.module.css';
import { MenuIcon } from './icons/MenuIcon';

export default function AppHeader({ onToggleSidebar }) {
  return (
    <header className={styles.header}>
      <Link to="/" className={styles.brand}>
        <img src="/logoS.png" alt="Serena Logo" className={styles.logo} />
        <span className={styles.brandName}>Serena</span>
      </Link>
      <button 
        onClick={onToggleSidebar} 
        className={styles.sidebarToggle}
        aria-label="Toggle menu"
      >
        <MenuIcon />
      </button>
    </header>
  );
}
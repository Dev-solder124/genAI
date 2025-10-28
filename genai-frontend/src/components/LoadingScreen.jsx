import React from 'react';
import styles from './LoadingScreen.module.css';

export default function LoadingScreen({ text = "Loading..." }) {
  return (
    <div className={styles.loadingContainer}>
      <img 
        src="/logoS.png" 
        alt="Serena Logo" 
        className={styles.loadingLogo} 
      />
      <p className={styles.loadingText}>{text}</p>
    </div>
  );
}
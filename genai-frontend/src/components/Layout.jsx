import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signOut } from '../lib/auth';
import styles from './Layout.module.css';

export default function Layout({ children }) {
    const navigate = useNavigate();

    const handleSignOut = async () => {
        await signOut();
        navigate('/login');
    };

    return (
        <div className={styles.layout}>
            <header className={styles.header}>
                <div className={styles.brand}>EmpathicAI</div>
                <nav className={styles.nav}>
                    <Link to="/chat" className={styles.navLink}>Chat</Link>
                    <Link to="/settings" className={styles.navLink}>Settings</Link>
                </nav>
                <button onClick={handleSignOut} className={styles.signOutButton}>
                    Sign Out
                </button>
            </header>
            <main className={styles.main}>
                {children}
            </main>
        </div>
    );
}

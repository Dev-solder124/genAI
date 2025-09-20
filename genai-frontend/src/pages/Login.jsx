import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { signInWithGoogle, signInAsGuest } from '../lib/auth'; // We will create this auth library
import styles from './Login.module.css';

export default function Login() {
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    const handleGoogleLogin = async () => {
        try {
            await signInWithGoogle();
            navigate('/chat');
        } catch (err) {
            setError(err.message);
        }
    };

    const handleGuestLogin = async () => {
        try {
            await signInAsGuest();
            navigate('/chat');
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1 className={styles.title}>EmpathicAI</h1>
                <p className={styles.subtitle}>Your empathetic AI companion</p>
                {error && <p className={styles.error}>{error}</p>}
                <button onClick={handleGoogleLogin} className={styles.googleButton}>
                    Sign in with Google
                </button>
                <button onClick={handleGuestLogin} className={styles.guestButton}>
                    Continue as Guest
                </button>
            </div>
        </div>
    );
}

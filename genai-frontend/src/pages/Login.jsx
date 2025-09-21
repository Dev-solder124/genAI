import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { signInWithGoogle, signInAsGuest } from '../lib/auth'; // We will create this auth library
import styles from './Login.module.css';

export default function Login() {
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);

    const handleGoogleLogin = async () => {
        setLoading(true);
        setError(null);
        try {
            await signInWithGoogle();
            navigate('/chat');
        } catch (err) {
            console.error('Google login error:', err);
            setError(
                err.code === 'auth/popup-closed-by-user'
                    ? 'Sign in was cancelled. Please try again.'
                    : err.code === 'auth/network-request-failed'
                    ? 'Network error. Please check your connection.'
                    : 'Failed to sign in with Google. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    };

    const handleGuestLogin = async () => {
        setLoading(true);
        setError(null);
        try {
            await signInAsGuest();
            navigate('/chat');
        } catch (err) {
            console.error('Guest login error:', err);
            setError(
                err.code === 'auth/network-request-failed'
                    ? 'Network error. Please check your connection.'
                    : 'Failed to continue as guest. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1 className={styles.title}>Serena</h1>
                <p className={styles.subtitle}>Your wellness wingman</p>
                {error && <p className={styles.error}>{error}</p>}
                <button 
                    onClick={handleGoogleLogin} 
                    className={`${styles.googleButton} ${loading ? styles.loading : ''}`}
                    disabled={loading}
                >
                    {loading ? 'Signing in...' : 'Sign in with Google'}
                </button>
                <button 
                    onClick={handleGuestLogin} 
                    className={`${styles.guestButton} ${loading ? styles.loading : ''}`}
                    disabled={loading}
                >
                    {loading ? 'Setting up...' : 'Continue as Guest'}
                </button>
            </div>
        </div>
    );
}

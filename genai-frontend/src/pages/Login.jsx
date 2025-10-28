import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { signInWithGoogle, signInAsGuest } from '../lib/auth';
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
                {/* Logo */}
                <img src="/logoS.png" alt="Serena Logo" className={styles.logo} />
                
                {/* Title */}
                <h1 className={styles.title}>Welcome Back</h1>
                <p className={styles.subtitle}>Continue your mental health journey</p>
                
                {/* Error Message */}
                {error && <div className={styles.error}>{error}</div>}
                
                {/* Google Sign In Button */}
                <button 
                    onClick={handleGoogleLogin} 
                    className={`${styles.googleButton} ${loading ? styles.loading : ''}`}
                    disabled={loading}
                >
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M19.6 10.23c0-.82-.1-1.42-.25-2.05H10v3.72h5.5c-.15.96-.74 2.31-2.04 3.22v2.45h3.16c1.89-1.73 2.98-4.3 2.98-7.34z"/>
                        <path d="M10 20c2.7 0 4.96-.89 6.62-2.42l-3.22-2.45c-.89.59-2.03.94-3.4.94-2.61 0-4.82-1.74-5.61-4.09H1.24v2.52C2.82 17.6 6.18 20 10 20z"/>
                        <path d="M4.39 11.98c-.22-.59-.35-1.22-.35-1.98s.13-1.39.35-1.98V5.5H1.24C.45 6.93 0 8.43 0 10s.45 3.07 1.24 4.5l3.15-2.52z"/>
                        <path d="M10 3.88c1.48 0 2.75.51 3.77 1.46l2.67-2.67C14.96.99 12.7 0 10 0 6.18 0 2.82 2.4 1.24 5.5l3.15 2.52C5.18 5.62 7.39 3.88 10 3.88z"/>
                    </svg>
                    {loading ? 'Signing in...' : 'Sign in with Google'}
                </button>
                
                {/* Divider */}
                <div className={styles.divider}>
                    <span>OR</span>
                </div>
                
                {/* Guest Sign In Button */}
                <button 
                    onClick={handleGuestLogin} 
                    className={`${styles.guestButton} ${loading ? styles.loading : ''}`}
                    disabled={loading}
                >
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M10 10c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                    {loading ? 'Setting up...' : 'Continue as Guest'}
                </button>
                
                {/* Privacy Notice */}
                <p className={styles.privacyNotice}>
                    By continuing, you agree to our{' '}
                    <a href="#" className={styles.privacyLink}>Terms of Service</a>
                    {' '}and{' '}
                    <a href="#" className={styles.privacyLink}>Privacy Policy</a>
                </p>
                
                {/* Back Button */}
                <button 
                    onClick={() => navigate('/')} 
                    className={styles.backButton}
                >
                    ← Back to Home
                </button>
            </div>
        </div>
    );
}
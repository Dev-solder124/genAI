// Updated Login.jsx - Better handling for guest authentication
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { signInWithGoogle, signInAsGuest } from '../lib/auth';
import styles from './Login.module.css';

export default function Login() {
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { user } = useAuth();

    // Redirect if already authenticated
    useEffect(() => {
        if (user) {
            console.log('Login: User already authenticated, redirecting...');
            navigate('/chat');
        }
    }, [user, navigate]);

    const handleGoogleLogin = async () => {
        setLoading(true);
        setError(null);
        console.log('Login: Starting Google authentication...');
        
        try {
            const user = await signInWithGoogle();
            console.log('Login: Google authentication successful:', user.uid);
            // Navigation will be handled by useEffect
        } catch (err) {
            console.error('Login: Google authentication error:', err);
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
        console.log('Login: Starting guest authentication...');
        
        try {
            const user = await signInAsGuest();
            console.log('Login: Guest authentication successful:', user.uid);
            
            // Add a small delay to ensure the auth state has propagated
            setTimeout(() => {
                if (user) {
                    console.log('Login: Navigating to chat after guest login');
                    navigate('/chat');
                }
            }, 1000);
            
        } catch (err) {
            console.error('Login: Guest authentication error:', err);
            setError(
                err.code === 'auth/network-request-failed'
                    ? 'Network error. Please check your connection.'
                    : err.code === 'auth/anonymous-signin-failed'
                    ? 'Failed to continue as guest. Please try refreshing the page.'
                    : 'Failed to continue as guest. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    };

    // Show loading if already authenticated
    if (user) {
        return (
            <div className={styles.container}>
                <div className={styles.loginBox}>
                    <h1 className={styles.title}>Serena</h1>
                    <p>Redirecting to chat...</p>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1 className={styles.title}>Serena</h1>
                <p className={styles.subtitle}>Friend Who Listens</p>
                
                {error && (
                    <div className={styles.error}>
                        <p>{error}</p>
                        {error.includes('guest') && (
                            <p style={{ fontSize: '0.9em', marginTop: '8px' }}>
                                Try refreshing the page or signing in with Google instead.
                            </p>
                        )}
                    </div>
                )}
                
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
                    {loading ? 'Setting up guest access...' : 'Continue as Guest'}
                </button>
            </div>
        </div>
    );
}
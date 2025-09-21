import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import styles from './Settings.module.css';

// Mock API - replace with your actual API calls
const mockApi = {
    getUserProfile: async (token) => ({
        profile: { consent: true, username: 'Demo User' }
    }),
    setConsent: async (token, consent) => {
        console.log('Setting consent to', consent);
        return true;
    }
};

export default function Settings() {
    const { user } = useAuth();
    const [consent, setConsent] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfile = async () => {
            if (user) {
                const token = await user.getIdToken();
                const profile = await mockApi.getUserProfile(token);
                setConsent(profile.profile.consent);
                setLoading(false);
            }
        };
        fetchProfile();
    }, [user]);

    const handleConsentChange = async () => {
        const newConsent = !consent;
        const token = await user.getIdToken();
        await mockApi.setConsent(token, newConsent);
        setConsent(newConsent);
    };

    if (loading) {
        return <div>Loading settings...</div>;
    }

    return (
        <div className={styles.settingsContainer}>
            <h2>Settings</h2>
            <div className={styles.setting}>
                <p><strong>Conversation Memory</strong></p>
                <p>Allow EmpathicAI to remember your conversations to provide a better experience.</p>
                <button onClick={handleConsentChange}>
                    {consent ? 'Disable Memory' : 'Enable Memory'}
                </button>
            </div>
        </div>
    );
}

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import styles from './Settings.module.css';

import { api } from '../lib/api';

export default function Settings() {
    const { user } = useAuth();
    const [consent, setConsent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [updating, setUpdating] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        const fetchProfile = async () => {
            if (user) {
                try {
                    console.log('Settings: Fetching profile using login endpoint');
                    // FIXED: Use login endpoint to READ profile without updating
                    const profile = await api.login();
                    console.log('Settings: Profile response:', profile);
                    setConsent(profile.profile?.consent);
                    setLoading(false);
                } catch (error) {
                    console.error('Error fetching profile:', error);
                    setError('Failed to load settings. Please refresh the page.');
                    setLoading(false);
                }
            }
        };
        fetchProfile();
    }, [user]);

    const handleDeleteMemories = async () => {
        if (window.confirm('Are you sure you want to delete all your memories? This action cannot be undone.')) {
            setDeleting(true);
            setError(null);
            try {
                await api.deleteMemories({ user_id: user.uid });
                alert('Your memories have been deleted.');
            } catch (error) {
                console.error('Error deleting memories:', error);
                setError('Failed to delete memories. Please try again.');
            } finally {
                setDeleting(false);
            }
        }
    };

    const handleConsentChange = async () => {
        setUpdating(true);
        setError(null);
        try {
            const newConsent = !consent;
            console.log('Settings: Updating consent to:', newConsent);
            
            // FIXED: Only call consent endpoint when actually updating
            const response = await api.consent({
                user_id: user.uid,
                consent: newConsent,
                username: user.displayName || 'User'
            });
            
            console.log('Settings: Consent update response:', response);
            
            if (response.profile?.consent !== undefined) {
                setConsent(response.profile.consent);
                console.log('Settings: Consent successfully updated to:', response.profile.consent);
            } else {
                throw new Error('Invalid server response');
            }
        } catch (error) {
            console.error('Error updating consent:', error);
            setError('Failed to update memory settings. Please try again.');
            // Keep the previous consent state
        } finally {
            setUpdating(false);
        }
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
                <p><em>Current status: {consent === true ? 'Enabled' : consent === false ? 'Disabled' : 'Not set'}</em></p>
                {error && <p className={styles.error}>{error}</p>}
                <button
                    onClick={handleConsentChange}
                    disabled={updating}
                    className={updating ? styles.loading : ''}
                >
                    {updating ? 'Updating...' : (consent ? 'Disable Memory' : 'Enable Memory')}
                </button>
            </div>
            <div className={styles.setting}>
                <p><strong>Delete Memories</strong></p>
                <p>This will permanently delete all of your stored conversation memories.</p>
                <button
                    onClick={handleDeleteMemories}
                    disabled={deleting}
                    className={`${deleting ? styles.loading : ''} ${styles.deleteButton}`}
                >
                    {deleting ? 'Deleting...' : 'Delete All Memories'}
                </button>
            </div>
        </div>
    );
}
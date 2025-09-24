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
    const [userProfile, setUserProfile] = useState(null);

    useEffect(() => {
        const fetchProfile = async () => {
            if (user) {
                try {
                    setLoading(true);
                    setError(null);
                    console.log('Settings: Fetching profile using login endpoint');
                    
                    // Use login endpoint to get the full profile
                    const profileResponse = await api.login();
                    console.log('Settings: Full profile response:', profileResponse);
                    
                    setUserProfile(profileResponse);
                    
                    // Extract consent from the nested profile structure
                    const consentValue = profileResponse.profile?.consent;
                    console.log('Settings: Extracted consent value:', consentValue);
                    
                    setConsent(consentValue);
                    setLoading(false);
                } catch (error) {
                    console.error('Settings: Error fetching profile:', error);
                    setError('Failed to load settings. Please refresh the page.');
                    setLoading(false);
                }
            }
        };
        fetchProfile();
    }, [user]);

    const handleConsentChange = async () => {
        if (!user) {
            setError('User not authenticated');
            return;
        }

        setUpdating(true);
        setError(null);
        
        try {
            const newConsent = !consent;
            console.log('Settings: Updating consent from', consent, 'to', newConsent);
            
            // Call the consent endpoint with the required fields
            const response = await api.consent({
                consent: newConsent,
                username: user.displayName || user.email || 'User' // Use Firebase user info
            });
            
            console.log('Settings: Consent update response:', response);
            
            // Update the local state with the new consent value
            if (response && response.profile) {
                setConsent(response.profile.consent);
                setUserProfile(response);
                console.log('Settings: Consent successfully updated to:', response.profile.consent);
            } else {
                throw new Error('Invalid server response - missing profile data');
            }
        } catch (error) {
            console.error('Settings: Error updating consent:', error);
            
            // Provide more specific error messages
            if (error.message?.includes('401') || error.message?.includes('unauthorized')) {
                setError('Session expired. Please refresh the page and sign in again.');
            } else if (error.message?.includes('network') || error.message?.includes('fetch')) {
                setError('Network error. Please check your connection and try again.');
            } else {
                setError('Failed to update memory settings. Please try again.');
            }
            
            // Keep the previous consent state on error
        } finally {
            setUpdating(false);
        }
    };

    // Show loading state
    if (loading) {
        return (
            <div className={styles.settingsContainer}>
                <h2>Settings</h2>
                <div>Loading settings...</div>
            </div>
        );
    }

    // Show error state if user is not available
    if (!user) {
        return (
            <div className={styles.settingsContainer}>
                <h2>Settings</h2>
                <div>Please sign in to access settings.</div>
            </div>
        );
    }

    return (
        <div className={styles.settingsContainer}>
            <h2>Settings</h2>
            
            {/* Debug information (you can remove this in production) */}
            {process.env.NODE_ENV === 'development' && (
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '20px', padding: '10px', border: '1px solid #ddd' }}>
                    <strong>Debug Info:</strong><br />
                    User ID: {user?.uid}<br />
                    Consent Value: {consent === null ? 'null' : consent.toString()}<br />
                    Profile Loaded: {userProfile ? 'Yes' : 'No'}<br />
                </div>
            )}
            
            <div className={styles.setting}>
                <p><strong>Conversation Memory</strong></p>
                <p>Allow Serena to remember your conversations to provide a better experience.</p>
                <p><em>Current status: {
                    consent === true ? 'Enabled' : 
                    consent === false ? 'Disabled' : 
                    'Not set'
                }</em></p>
                
                {error && <p className={styles.error}>{error}</p>}
                
                <button 
                    onClick={handleConsentChange}
                    disabled={updating || consent === null}
                    className={updating ? styles.loading : ''}
                >
                    {updating ? 'Updating...' : 
                     consent === null ? 'Set Preference' :
                     consent ? 'Disable Memory' : 'Enable Memory'}
                </button>
            </div>

            {/* Additional settings can be added here */}
            <div className={styles.setting}>
                <p><strong>Account Information</strong></p>
                <p>Username: {userProfile?.profile?.username || 'Not set'}</p>
                <p>Account created: {userProfile?.profile?.created_at ? 
                    new Date(userProfile.profile.created_at).toLocaleDateString() : 
                    'Unknown'}</p>
            </div>
        </div>
    );
}
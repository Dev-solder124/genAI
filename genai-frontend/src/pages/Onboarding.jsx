import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import styles from './Chat.module.css'; // We'll re-use the CSS from Chat.module.css

export default function Onboarding() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [error, setError] = useState(null);

    const handleConsent = async (consent) => {
        try {
            setError(null);
            console.log('Onboarding: Setting consent to:', consent);
            
            const response = await api.consent({
                user_id: user.uid,
                consent: consent,
                username: user.displayName || 'User'
            });
            
            console.log('Onboarding: Consent response:', response);
            
            // Success! Redirect to the chat page.
            navigate('/chat', { replace: true });

        } catch (error) {
            console.error('Error setting consent:', error);
            const errorMessage = "Sorry, I couldn't save your preferences. Please try again.";
            setError(errorMessage);
        }
    };

    // The return is no longer conditional. This page's only job is to ask for consent.
    return (
  <div className={styles.container}>
    <div className={styles.card}>   {/* <-- card wrapper */}
      <h2>Privacy & Memory Settings</h2>
      <p>Serena can remember important parts of our conversations to provide better, more personalized support over time.</p>
      <p>Your privacy matters. You can delete your data anytime from the settings page.</p>

      {error && <p className={styles.errorMessage}>{error}</p>}

      <div className={styles.consentButtons}>
        <button onClick={() => handleConsent(true)}>Remember Conversations</button>
        <button onClick={() => handleConsent(false)}>Forget Conversations</button>
      </div>
    </div>
  </div>
);
}
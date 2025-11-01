import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { signOut } from '../lib/auth';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import styles from './Sidebar.module.css';
import { CloseIcon } from './icons/CloseIcon';
import ToggleSwitch from './ToggleSwitch'; // Import the new toggle

export default function Sidebar({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { user } = useAuth();

  // State for settings
  const [consent, setConsent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [resetting, setResetting] = useState(false);

  // Fetch profile when sidebar opens
  useEffect(() => {
    const fetchProfile = async () => {
      if (user && isOpen) {
        setLoading(true);
        setError(null);
        try {
          const profile = await api.login();
          setConsent(profile.profile?.consent);
          setLoading(false);
        } catch (error) {
          setError('Failed to load settings.');
          setLoading(false);
        }
      }
    };
    fetchProfile();
  }, [user, isOpen]);

  // --- Settings Handlers ---
  const handleConsentChange = async () => {
    setUpdating(true);
    setError(null);
    const newConsent = !consent;
    try {
      const response = await api.consent({
        user_id: user.uid,
        consent: newConsent,
        username: user.displayName || 'User'
      });
      if (response.profile?.consent !== undefined) {
        setConsent(response.profile.consent);
      } else {
        throw new Error('Invalid server response');
      }
    } catch (error) {
      setError('Failed to update memory settings.');
      // Revert on failure
      setConsent(!newConsent);
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteMemories = async () => {
    if (window.confirm('Are you sure you want to delete all your memories? This action cannot be undone.')) {
      setDeleting(true);
      setError(null);
      try {
        await api.deleteMemories({ user_id: user.uid });
        alert('Your memories have been deleted.');
      } catch (error) {
        setError('Failed to delete memories.');
      } finally {
        setDeleting(false);
      }
    }
  };

  const handleResetInstructions = async () => {
    if (window.confirm('Are you sure you want to reset Serena? This will clear all custom instructions.')) {
      setResetting(true);
      setError(null);
      try {
        await api.resetInstructions();
        alert('Serena has been reset.');
      } catch (error) {
        setError('Failed to reset instructions.');
      } finally {
        setResetting(false);
      }
    }
  };

  // --- Sign Out Handler ---
  const handleSignOut = async () => {
    onClose();
    await signOut();
    navigate('/login');
  };

  return (
    <>
      <div 
        className={`${styles.overlay} ${isOpen ? styles.overlayOpen : ''}`} 
        onClick={onClose}
        aria-hidden="true"
      />
      
      <aside className={`${styles.sidebar} ${isOpen ? styles.sidebarOpen : ''}`}>
        
        {/* HEADER: Title and close button on the same line */}
        <div className={styles.sidebarHeader}>
          <h3 className={styles.headerTitle}>Settings</h3>
          <button onClick={onClose} className={styles.closeButton} aria-label="Close menu">
            <CloseIcon />
          </button>
        </div>
        
        {/* SETTINGS SECTION: Styled as a clean list */}
        <nav className={styles.sidebarNav}>
          {/* <h4 className={styles.sectionTitle}>Settings</h4> <-- REMOVED FROM HERE */}
          
          {error && <p className={styles.error}>{error}</p>}
          
          <div className={styles.navItem}>
            <span>Conversation Memory</span>
            <ToggleSwitch
              id="consent-toggle"
              isOn={consent}
              handleToggle={handleConsentChange}
              disabled={loading || updating}
            />
          </div>

          <div className={styles.navItem}>
            <span>Reset Serena</span>
            <button
              onClick={handleResetInstructions}
              disabled={resetting}
              className={styles.navButton}
              title="Restore default settings. This action cannot be undone!"
            >
              {resetting ? 'Resetting...' : 'Reset'}
            </button>
          </div>

          <div className={styles.navItem}>
            <span>Delete All Memories</span>
            <button
              onClick={handleDeleteMemories}
              disabled={deleting}
              className={`${styles.navButton} ${styles.deleteButton}`}
              title="Delete all your saved memories permanently. This action cannot be undone!"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </nav>

        {/* FOOTER: This is now pushed to the bottom */}
        <div className={styles.sidebarFooter}>
          <button onClick={handleSignOut} className={styles.signOutButton}>
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
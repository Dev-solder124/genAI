import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { signOut } from '../lib/auth';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import styles from './Sidebar.module.css';
import { CloseIcon } from './icons/CloseIcon';
import ToggleSwitch from './ToggleSwitch';

// --- NEW: Info Icon SVG Component ---
const InfoSvgIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <path d="M12 16v-4"></path>
    <path d="M12 8h.01"></path>
  </svg>
);

// --- NEW: Reusable InfoTooltip Component ---
const InfoTooltip = ({ content }) => {
  const [show, setShow] = useState(false);

  return (
    <div className={styles.infoIconWrapper}>
      <button
        className={styles.infoIcon}
        aria-label="More info"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(s => !s)} // Toggle on click
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
      >
        <InfoSvgIcon /> {/* Using the new SVG icon */}
      </button>
      {show && (
        <div className={styles.tooltip}>
          {content}
          <div className={styles.tooltipArrow}></div> {/* Arrow for styling */}
        </div>
      )}
    </div>
  );
};

// --- Content for Tooltips (from README.md) ---
const consentInfo = "Turn this on, and Serena will remember the important parts of your chats. This helps her understand you better and pick up where you left off next time.";

const resetInfo = "This makes Serena forget any special instructions you've given her. It's like meeting her again for the first time, so you can build a new connection.";

const deleteInfo = "This erases everything Serena remembers about your past conversations. This is permanent and cannot be undone.";

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

  // --- Settings Handlers (unchanged) ---
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
    if (window.confirm('Are you sure you want to reset Serena? This will clear all custom instructions and reset your conversation stage.')) {
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

  // --- Sign Out Handler (unchanged) ---
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
        
        {/* HEADER (unchanged) */}
        <div className={styles.sidebarHeader}>
          <h3 className={styles.headerTitle}>Settings</h3>
          <button onClick={onClose} className={styles.closeButton} aria-label="Close menu">
            <CloseIcon />
          </button>
        </div>
        
        {/* SETTINGS SECTION: Updated with info tooltips */}
        <nav className={styles.sidebarNav}>
          
          {error && <p className={styles.error}>{error}</p>}
          
          <div className={styles.navItem}>
            <div className={styles.navItemLabel}>
              <span>Conversation Memory</span>
              <InfoTooltip content={consentInfo} />
            </div>
            <ToggleSwitch
              id="consent-toggle"
              isOn={consent}
              handleToggle={handleConsentChange}
              disabled={loading || updating}
            />
          </div>

          <div className={styles.navItem}>
            <div className={styles.navItemLabel}>
              <span>Reset Serena</span>
              <InfoTooltip content={resetInfo} />
            </div>
            <button
              onClick={handleResetInstructions}
              disabled={resetting}
              className={styles.navButton}
            >
              {resetting ? 'Resetting...' : 'Reset'}
            </button>
          </div>

          <div className={styles.navItem}>
             <div className={styles.navItemLabel}>
              <span>Delete All Memories</span>
              <InfoTooltip content={deleteInfo} />
            </div>
            <button
              onClick={handleDeleteMemories}
              disabled={deleting}
              className={`${styles.navButton} ${styles.deleteButton}`}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </nav>

        {/* FOOTER (unchanged) */}
        <div className={styles.sidebarFooter}>
          <button onClick={handleSignOut} className={styles.signOutButton}>
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api'; // Assuming you have an API library
import styles from './Chat.module.css';
import { IconSend } from '../components/icons/IconSend';
import LoadingScreen from '../components/LoadingScreen';

// Initialize session ID for the chat
const SESSION_ID = `session_${Date.now()}`;

export default function Chat() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [userProfile, setUserProfile] = useState(null);
    const [consentNeeded, setConsentNeeded] = useState(false);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
    const [error, setError] = useState(null);
    const [sending, setSending] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    const adjustTextareaHeight = (element) => {
        if (!element) return;
        
        // Reset height to auto to get the correct scrollHeight
        element.style.height = 'auto';
        
        // Calculate the new height based on content, respecting min and max heights
        const scrollHeight = element.scrollHeight;
        const minHeight = 40; // Match the min-height in CSS
        const maxHeight = 150; // Match the max-height in CSS
        
        const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
        element.style.height = newHeight + 'px';
    };

    // Show loading state while auth is initializing
    if (loading) {
        return <LoadingScreen text="Loading your chat..." />;
    }

    // Redirect or show message if not authenticated
    if (!user) {
        return <div>Please log in to access the chat.</div>;
    }

    useEffect(() => {
        const fetchUserProfile = async () => {
            if (!user) {
                console.log('No user logged in');
                return;
            }

            try {
                console.log('Chat: Fetching profile for user:', user.uid);
                const response = await api.login();
                console.log('Chat: Profile response:', response);

                setUserProfile(response);
                if (response.profile?.consent === null) {
                    // Consent is missing, redirect to onboarding
                    console.log('Chat: Consent is null, redirecting to onboarding');
                    navigate('/onboarding', { replace: true });
                }
                // If consent is not null, we do nothing and the chat page loads normally.

            } catch (error) {
                console.error('Error fetching user profile:', error);
                setMessages(prev => [...prev, { 
                    role: 'bot', 
                    text: "Sorry, I'm having trouble connecting to the server. Please try again later." 
                }]);
            }
        };

        if (user) {
            fetchUserProfile();
        }
    }, [user, navigate]); // <-- ADD navigate to the dependency array


    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

        // Check if there are messages and the last one is from the bot
        if (messages.length > 0 && messages[messages.length - 1].role === 'bot') {
            // Re-focus the input field so the user can type immediately
            textareaRef.current?.focus();
        }
    }, [messages]);

    const handleSend = async () => {
        const trimmedInput = input.trim();
        if (trimmedInput === '' || sending) return;

        setError(null);
        setSending(true);
        const newMessage = { role: 'user', text: trimmedInput };
        setMessages(prev => [...prev, newMessage]);
        setInput('');
        
        // Reset textarea height after clearing input
        if (textareaRef.current) {
            setTimeout(() => {
                textareaRef.current.style.height = 'auto';
                textareaRef.current.style.height = '40px'; // Reset to min-height
            }, 0);
        }

        let attempts = 0;
        const maxAttempts = 3;
        const backoffDelay = 1000; // Start with 1 second delay

        const attemptSend = async () => {
            try {
                const response = await api.sendMessage({
                    user_id: user.uid,
                    session: SESSION_ID,
                    message: trimmedInput
                });
                
                const botResponse = response.fulfillment_response?.messages?.[0]?.text?.text?.[0];
                if (!botResponse) {
                    throw new Error('Invalid response format from server');
                }
                
                setMessages(prev => [...prev, { role: 'bot', text: botResponse }]);
                setRetryCount(0); // Reset retry count on success
                return true; // Success
            } catch (error) {
                console.error(`Error sending message (attempt ${attempts + 1}/${maxAttempts}):`, error);
                
                // Handle different error types
                if (error.code === 'unauthorized' || error.code === 'unauthenticated') {
                    throw new Error("Your session has expired. Please refresh the page and sign in again.");
                } else if (error.code === 'network_error' && attempts < maxAttempts - 1) {
                    attempts++;
                    const delay = backoffDelay * Math.pow(2, attempts - 1); // Exponential backoff
                    await new Promise(resolve => setTimeout(resolve, delay));
                    return false; // Retry
                } else {
                    throw new Error(error.code === 'network_error' 
                        ? "Network error. Please check your connection and try again."
                        : "Sorry, I couldn't process your message. Please try again.");
                }
            }
        };

        try {
            let success = false;
            while (!success && attempts < maxAttempts) {
                success = await attemptSend();
            }
        } catch (error) {
            setMessages(prev => [...prev, { 
                role: 'bot', 
                text: error.message
            }]);
            setError(error.message);
        } finally {
            setSending(false);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setInput(value);
        // Adjust height immediately as user types
        adjustTextareaHeight(e.target);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sending) handleSend();
        }
    };

    const handleConsent = async (consent) => {
        try {
            setError(null);
            console.log('Chat: Setting consent to:', consent);
            
            // FIXED: Now we're explicitly setting consent, not just reading
            const response = await api.consent({
                user_id: user.uid,
                consent: consent,
                username: user.displayName || 'User'
            });
            
            console.log('Chat: Consent response:', response);
            
            setConsentNeeded(false);
            setMessages([{ 
                role: 'bot', 
                text: consent ? 
                    "Thanks for letting me remember our conversations. I'll do my best to provide more personalized support. How can I help you today?" :
                    "I'll keep our conversations private and won't store any memory of them. How can I help you today?"
            }]);
        } catch (error) {
            console.error('Error setting consent:', error);
            const errorMessage = "Sorry, I couldn't save your preferences. Please try again.";
            setError(errorMessage);
            setMessages(prev => [...prev, { role: 'bot', text: errorMessage }]);
        }
    };

    if (consentNeeded) {
        return (
            <div className={styles.consentContainer}>
                <h2>Privacy & Memory Settings</h2>
                <p>EmpathicAI can remember important parts of our conversations to provide better, more personalized support over time.</p>
                <p>Your privacy matters. You can delete your data anytime.</p>
                <div className={styles.consentButtons}>
                    <button onClick={() => handleConsent(true)}>Remember Conversations</button>
                    <button onClick={() => handleConsent(false)}>Forget Conversations</button>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.chatContainer}>
            <div className={styles.messageList}>
                {messages.map((msg, index) => (
                    <div key={index} className={`${styles.message} ${styles[msg.role]}`}>
                        {msg.text}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <div className={styles.inputArea}>
                <textarea
                    ref={textareaRef}
                    className={styles.messageInput}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type your message..."
                    disabled={sending}
                    rows={1}
                    aria-label="Message input"
                />
                <button 
                onClick={handleSend}
                disabled={sending || !input.trim()}
                className={sending ? styles.loading : ''}
            >
                {sending ? <div className={styles.loadingSpinner}></div> : <IconSend />}
                </button>
            </div>
            {error && (
                <div className={styles.errorContainer}>
                    <p className={styles.errorMessage}>{error}</p>
                </div>
            )}
        </div>
    );
}
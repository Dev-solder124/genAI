import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import styles from './Chat.module.css';

// Initialize session ID for the chat
const SESSION_ID = `session_${Date.now()}`;

export default function Chat() {
    const { user, loading } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [userProfile, setUserProfile] = useState(null);
    const [consentNeeded, setConsentNeeded] = useState(false);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
    const [error, setError] = useState(null);
    const [sending, setSending] = useState(false);

    const adjustTextareaHeight = (element) => {
        if (!element) return;
        
        element.style.height = 'auto';
        const scrollHeight = element.scrollHeight;
        const minHeight = 40;
        const maxHeight = 150;
        const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
        element.style.height = newHeight + 'px';
    };

    // Show loading state while auth is initializing
    if (loading) {
        return <div>Loading...</div>;
    }

    // Redirect or show message if not authenticated
    if (!user) {
        return <div>Please log in to access the chat.</div>;
    }

    useEffect(() => {
        const fetchUserProfile = async () => {
            if (!user) {
                console.log('Chat: No user logged in');
                return;
            }

            try {
                console.log('Chat: Fetching profile for user:', user.uid);
                
                const response = await api.login();
                console.log('Chat: Profile response:', response);
                
                setUserProfile(response);
                
                const consentValue = response.profile?.consent;
                console.log('Chat: Consent value from profile:', consentValue);
                
                if (consentValue === null || consentValue === undefined) {
                    console.log('Chat: Consent is null/undefined, showing consent screen');
                    setConsentNeeded(true);
                } else {
                    console.log('Chat: Consent already set to:', consentValue);
                    setConsentNeeded(false);
                }
            } catch (error) {
                console.error('Chat: Error fetching user profile:', error);
                
                let errorMessage = "Sorry, I'm having trouble connecting to the server. Please try again later.";
                
                if (error.code === 'unauthorized' || error.code === 'unauthenticated') {
                    errorMessage = "Your session has expired. Please refresh the page and sign in again.";
                } else if (error.code === 'network_error') {
                    errorMessage = "Network error. Please check your connection and try again.";
                }
                
                setError(errorMessage);
                setMessages(prev => [...prev, { 
                    role: 'bot', 
                    text: errorMessage
                }]);
            }
        };

        if (user) {
            fetchUserProfile();
        }
    }, [user]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
                textareaRef.current.style.height = '40px';
            }, 0);
        }

        try {
            console.log('Chat: Sending message:', trimmedInput);
            
            const response = await api.sendMessage({
                session: SESSION_ID,
                message: trimmedInput
            });
            
            console.log('Chat: Message response:', response);
            
            // Extract response from the backend format
            const botResponse = response.fulfillment_response?.messages?.[0]?.text?.text?.[0];
            if (!botResponse) {
                throw new Error('Invalid response format from server');
            }
            
            setMessages(prev => [...prev, { role: 'bot', text: botResponse }]);
            
        } catch (error) {
            console.error('Chat: Error sending message:', error);
            
            let errorMessage = "Sorry, I couldn't process your message. Please try again.";
            
            if (error.code === 'unauthorized' || error.code === 'unauthenticated') {
                errorMessage = "Your session has expired. Please refresh the page and sign in again.";
            } else if (error.code === 'network_error') {
                errorMessage = "Network error. Please check your connection and try again.";
            } else if (error.code === 'rate_limited') {
                errorMessage = "Too many requests. Please wait a moment before trying again.";
            }
            
            setMessages(prev => [...prev, { 
                role: 'bot', 
                text: errorMessage
            }]);
            setError(errorMessage);
        } finally {
            setSending(false);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setInput(value);
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
            
            const response = await api.consent({
                consent: consent,
                username: user.displayName || user.email || 'User'
            });
            
            console.log('Chat: Consent response:', response);
            
            setConsentNeeded(false);
            setUserProfile(response);
            
            setMessages([{ 
                role: 'bot', 
                text: consent ? 
                    "Thanks for letting me remember our conversations. I'll do my best to provide more personalized support. How can I help you today?" :
                    "I'll keep our conversations private and won't store any memory of them. How can I help you today?"
            }]);
        } catch (error) {
            console.error('Chat: Error setting consent:', error);
            
            let errorMessage = "Sorry, I couldn't save your preferences. Please try again.";
            
            if (error.code === 'unauthorized' || error.code === 'unauthenticated') {
                errorMessage = "Your session has expired. Please refresh the page and sign in again.";
            } else if (error.code === 'network_error') {
                errorMessage = "Network error. Please check your connection and try again.";
            }
            
            setError(errorMessage);
            setMessages(prev => [...prev, { role: 'bot', text: errorMessage }]);
        }
    };

    if (consentNeeded) {
        return (
            <div className={styles.consentContainer}>
                <h2>Privacy & Memory Settings</h2>
                <p>Serena can remember important parts of our conversations to provide better, more personalized support over time.</p>
                <p>Your privacy matters. You can delete your data anytime in Settings.</p>
                {error && <p className={styles.error}>{error}</p>}
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
                    {sending ? 'Sending...' : 'Send'}
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
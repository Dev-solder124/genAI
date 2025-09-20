import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api'; // Assuming you have an API library
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
                console.log('No user logged in');
                return;
            }

            try {
                console.log('Fetching profile for user:', user.uid);
                const response = await api.consent({
                    user_id: user.uid,
                    consent: null,
                    username: user.displayName || 'New User'
                });
                console.log('Profile response:', response);
                
                setUserProfile(response);
                if (response.profile?.consent === null) {
                    setConsentNeeded(true);
                }
            } catch (error) {
                console.error('Error fetching user profile:', error);
                // Show error message to user
                setMessages(prev => [...prev, { 
                    role: 'bot', 
                    text: "Sorry, I'm having trouble connecting to the server. Please try again later." 
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
        if (input.trim() === '') return;

        const newMessage = { role: 'user', text: input };
        setMessages(prev => [...prev, newMessage]);
        setInput('');

        try {
            const response = await api.sendMessage({
                user_id: user.uid,
                session: SESSION_ID,
                message: input
            });
            
            const botResponse = response.fulfillment_response?.messages?.[0]?.text?.text?.[0] || 
                              "I'm having trouble understanding. Could you try again?";
            
            setMessages(prev => [...prev, { role: 'bot', text: botResponse }]);
        } catch (error) {
            console.error('Error sending message:', error);
            setMessages(prev => [...prev, { 
                role: 'bot', 
                text: "Sorry, I couldn't process your message. Please try again." 
            }]);
        }
    };

    const handleConsent = async (consent) => {
        try {
            await api.consent({
                user_id: user.uid,
                consent: consent,
                username: user.displayName || 'User'
            });
            setConsentNeeded(false);
            setMessages([{ 
                role: 'bot', 
                text: "Thanks for setting your preferences. How can I help you today?" 
            }]);
        } catch (error) {
            console.error('Error setting consent:', error);
            setMessages([{ 
                role: 'bot', 
                text: "Sorry, I couldn't save your preferences. Please try again later." 
            }]);
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
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Type your message..."
                />
                <button onClick={handleSend}>Send</button>
            </div>
        </div>
    );
}

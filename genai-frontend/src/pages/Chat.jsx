import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api'; // Assuming you have an API library
import styles from './Chat.module.css';

// Mock API for now - replace with your actual API calls
const mockApi = {
    getUserProfile: async (token) => ({
        profile: { consent: null, username: 'New User' } 
    }),
    setConsent: async (token, consent) => {
        console.log('Setting consent to', consent);
        return true;
    },
    sendMessage: async (token, message) => {
        console.log('Sending message:', message);
        return `Echo: ${message}`;
    }
};

export default function Chat() {
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [userProfile, setUserProfile] = useState(null);
    const [consentNeeded, setConsentNeeded] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        const fetchUserProfile = async () => {
            if (user) {
                const token = await user.getIdToken();
                // Replace with your actual API call
                const profile = await mockApi.getUserProfile(token);
                setUserProfile(profile);
                if (profile.profile.consent === null) {
                    setConsentNeeded(true);
                }
            }
        };
        fetchUserProfile();
    }, [user]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        if (input.trim() === '') return;

        const newMessage = { role: 'user', text: input };
        setMessages(prev => [...prev, newMessage]);
        setInput('');

        const token = await user.getIdToken();
        // Replace with your actual API call
        const botResponse = await mockApi.sendMessage(token, input);
        
        setMessages(prev => [...prev, { role: 'bot', text: botResponse }]);
    };

    const handleConsent = async (consent) => {
        const token = await user.getIdToken();
        // Replace with your actual API call
        await mockApi.setConsent(token, consent);
        setConsentNeeded(false);
        setMessages([{ role: 'bot', text: "Thanks for setting your preferences. How can I help you today?" }]);
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

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import { PulseLoader } from 'react-spinners';

import styles from './Landing.module.css';
import { signInWithGoogle, signInAsGuest } from '../lib/auth';

// Throttle helper function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

export default function Landing() {
    const navigate = useNavigate();
    const scrollContainerRef = useRef(null);
    const intervalRef = useRef(null);
    const [isAutoplayPaused, setIsAutoplayPaused] = useState(false);

    // State for Login Logic
    const [loadingGoogle, setLoadingGoogle] = useState(false);
    const [loadingGuest, setLoadingGuest] = useState(false);
    const [error, setError] = useState(null);

    // Login Handlers
    const handleGoogleLogin = async () => {
        setLoadingGoogle(true);
        setError(null);
        try {
            await signInWithGoogle();
            navigate('/chat');
        } catch (err) {
            console.error('Google login error:', err);
            setError(
                err.code === 'auth/popup-closed-by-user'
                    ? 'Sign in was cancelled.'
                    : err.code === 'auth/network-request-failed'
                    ? 'Network error. Check connection.'
                    : 'Failed to sign in with Google.'
            );
        } finally {
            setLoadingGoogle(false);
        }
    };

    const handleGuestLogin = async () => {
        setLoadingGuest(true);
        setError(null);
        try {
            await signInAsGuest();
            navigate('/chat');
        } catch (err) {
            console.error('Guest login error:', err);
            setError(
                err.code === 'auth/network-request-failed'
                    ? 'Network error. Check connection.'
                    : 'Failed to continue as guest.'
            );
        } finally {
            setLoadingGuest(false);
        }
    };

    const scrollToSection = (id) => {
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    };

    // Carousel Logic
    const findAndSetCenterCard = useCallback(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const containerCenter = container.getBoundingClientRect().left + container.offsetWidth / 2;
        let minDiff = Infinity;
        let centerCard = null;
        Array.from(container.children).forEach((card) => {
            const cardCenter = card.getBoundingClientRect().left + card.offsetWidth / 2;
            const diff = Math.abs(containerCenter - cardCenter);
            if (diff < minDiff) {
                minDiff = diff;
                centerCard = card;
            }
            card.classList.remove(styles.isCenter);
        });
        if (centerCard) {
            centerCard.classList.add(styles.isCenter);
        }
    }, []);

    const throttledFindCenter = throttle(findAndSetCenterCard, 100);

    const startAutoplay = useCallback(() => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = setInterval(() => {
            const container = scrollContainerRef.current;
            if (!container || container.children.length === 0) return;
            const firstCard = container.children[0];
            const gap = parseInt(window.getComputedStyle(container).gap) || 32;
            const scrollAmount = firstCard.offsetWidth + gap;
            const atEnd = container.scrollLeft + container.offsetWidth >= container.scrollWidth - (scrollAmount / 2);
            if (atEnd) {
                container.scrollTo({ left: 0, behavior: 'instant' });
            } else {
                container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            }
        }, 4000);
    }, []);

    const stopAutoplay = () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
    };

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const handleMouseEnter = () => setIsAutoplayPaused(true);
        const handleMouseLeave = () => setIsAutoplayPaused(false);
        const handleTouchStart = () => setIsAutoplayPaused(true);
        container.addEventListener('mouseenter', handleMouseEnter);
        container.addEventListener('mouseleave', handleMouseLeave);
        container.addEventListener('scroll', throttledFindCenter);
        container.addEventListener('touchstart', handleTouchStart, { passive: true });
        findAndSetCenterCard();
        return () => {
            stopAutoplay();
            container.removeEventListener('mouseenter', handleMouseEnter);
            container.removeEventListener('mouseleave', handleMouseLeave);
            container.removeEventListener('scroll', throttledFindCenter);
            container.removeEventListener('touchstart', handleTouchStart);
        };
    }, [findAndSetCenterCard, throttledFindCenter]);

    useEffect(() => {
        if (!isAutoplayPaused) {
            startAutoplay();
        } else {
            stopAutoplay();
        }
        return () => stopAutoplay();
    }, [isAutoplayPaused, startAutoplay]);

    return (
        <main className={styles.landingContainer}>
            <Helmet>
                <title>Serena AI - Mental Health Chatbot with Intelligent Memory | Student Research Project</title>
                <meta name="description" content="Explore Serena, an AI mental health companion with intelligent memory. A student research project demonstrating advanced conversational AI and secure data handling." />
                <meta name="keywords" content="AI therapy chatbot, mental health support, intelligent memory assistant, student AI project, conversational AI research" />
                <meta property="og:title" content="Serena AI - Intelligent Mental Health Companion" />
                <meta property="og:description" content="Student-built AI mental health chatbot with memory capabilities" />
                <meta property="og:image" content="/logoS.png" />
                <meta property="og:type" content="website" />
                <meta name="twitter:card" content="summary" />
                <meta name="twitter:title" content="Serena AI Mental Health Chatbot" />
                <meta name="twitter:description" content="AI-powered mental health support with intelligent memory" />
                <script type="application/ld+json">
                {`
                {
                    "@context": "https://schema.org",
                    "@type": "SoftwareApplication",
                    "name": "Serena AI",
                    "applicationCategory": "HealthApplication",
                    "operatingSystem": "Web",
                    "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
                    "description": "AI-powered mental health chatbot with intelligent memory - a student research project demonstrating conversational AI technology"
                }
                `}
                </script>
            </Helmet>
            
            {/* Navigation */}
            <header className={styles.nav}>
                <div className={styles.navContent}>
                    <div className={styles.navBrand}>
                        <img src="/logoS.png" alt="Serena Logo" className={styles.navLogo} />
                        <span className={styles.brandName}>Serena</span>
                    </div>
                    <div className={styles.navLinks}>
                        <button onClick={() => scrollToSection('features')} className={styles.navLink}>
                            Features
                        </button>
                        <button onClick={() => scrollToSection('how-it-works')} className={styles.navLink}>
                            How It Works
                        </button>
                        {/* --- NEWLY ADDED LINKS --- */}
                        <button onClick={() => scrollToSection('about')} className={styles.navLink}>
                            Who It's For
                        </button>
                        <button onClick={() => scrollToSection('faq')} className={styles.navLink}>
                            FAQ
                        </button>
                         {/* --- END NEWLY ADDED LINKS --- */}
                    </div>
                    <div className={styles.navButtons}>
                        <Link to="/login" className={styles.getStartedButton}>
                            Sign In
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className={styles.hero}>
                <article className={styles.heroContent}>
                    <div className={styles.heroText}>
                        <h1 className={styles.heroTitle}>
                            Meet Serena - Your Intelligent Mental Health Companion
                        </h1>
                        <p className={styles.heroSubtitle}>
                            Talk. Be heard. Figure it out. Powered by clinically-grounded support that listens without judgment, remembers what matters, and empowers YOU to find your own answers.
                        </p>
                        
                        <div className={styles.credibilitySection}>
                            <div className={styles.badges}>
                                <span className={styles.badge}>24/7 Support</span>
                                <span className={styles.badge}>Clinically Grounded</span>
                                <span className={styles.badge}>Your Data, Encrypted & Private</span>
                            </div>
                        </div>

                        <div className={styles.heroCtas}>
                            <button
                                onClick={handleGoogleLogin}
                                className={`${styles.heroGoogleButton} ${loadingGoogle ? styles.loading : ''}`}
                                disabled={loadingGoogle || loadingGuest}
                            >
                                {loadingGoogle ? (
                                    <PulseLoader size={8} color={"var(--primary-brown-dark)"} />
                                ) : (
                                    <>
                                        <img src="/logos/google.svg" alt="Google" className={styles.buttonIcon} />
                                        <span>Login with Google</span>
                                    </>
                                )}
                            </button>
                            <button
                                onClick={handleGuestLogin}
                                className={`${styles.heroGuestButton} ${loadingGuest ? styles.loading : ''}`}
                                disabled={loadingGoogle || loadingGuest}
                            >
                                {loadingGuest ? (
                                   <PulseLoader size={8} color={"var(--white)"} />
                                ) : (
                                    <span>Continue as Guest</span>
                                )}
                            </button>
                        </div>
                        {error && <div className={styles.heroError}>{error}</div>}
                    </div>
                    <div className={styles.heroVisual}>
                        <img src="/logoS.png" alt="Serena AI Logo" className={styles.heroLogoPulse} />
                    </div>
                </article>
            </section>
            
            {/* Features Section */}
            <section id="features" className={styles.features}>
                <h2 className={styles.sectionTitle}>Intelligent Support That Remembers</h2>
                
                <div 
                    className={styles.featuresGrid}
                    ref={scrollContainerRef}
                >
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M24 4C18.5 4 14 8.5 14 14V20C14 25.5 18.5 30 24 30C29.5 30 34 25.5 34 20V14C34 8.5 29.5 4 24 4Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M18 18C18 18 20 20 24 20C28 20 30 18 30 18" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <circle cx="20" cy="15" r="1.5" fill="#8B5A3C"/>
                                <circle cx="28" cy="15" r="1.5" fill="#8B5A3C"/>
                                <path d="M24 30V34M18 34H30M14 38H34" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Intelligent Memory System</h3>
                        <p className={styles.featureDescription}>
                            Serena remembers important details from your conversations, creating a continuous thread of understanding that deepens over time.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <circle cx="24" cy="24" r="18" stroke="#8B5A3C" strokeWidth="2.5"/>
                                <path d="M24 10V24L32 28" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Time-Aware Conversations</h3>
                        <p className={styles.featureDescription}>
                            Context-aware responses that understand when things happened and how they relate to your current situation.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <rect x="12" y="16" width="24" height="24" rx="3" stroke="#8B5A3C" strokeWidth="2.5"/>
                                <path d="M18 16V12C18 9.8 19.8 8 22 8H26C28.2 8 30 9.8 30 12V16" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <circle cx="24" cy="28" r="3" stroke="#8B5A3C" strokeWidth="2.5"/>
                                <path d="M24 31V35" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Privacy-First Design</h3>
                        <p className={styles.featureDescription}>
                            Your conversations are encrypted and secure. You control your data and can delete memories anytime.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <circle cx="20" cy="20" r="10" stroke="#8B5A3C" strokeWidth="2.5"/>
                                <path d="M28 28L38 38" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M15 20H25M20 15V25" stroke="#8B5A3C" strokeWidth="2" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Semantic Memory Retrieval</h3>
                        <p className={styles.featureDescription}>
                            Advanced AI understands meaning, not just keywords, retrieving relevant memories when they matter most.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M24 8C16 8 10 14 10 22C10 26 12 29.5 15 31.5V38L20 35L24 37L28 35L33 38V31.5C36 29.5 38 26 38 22C38 14 32 8 24 8Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <circle cx="18" cy="20" r="2" fill="#8B5A3C"/>
                                <circle cx="30" cy="20" r="2" fill="#8B5A3C"/>
                                <path d="M18 26C18 26 20 28 24 28C28 28 30 26 30 26" stroke="#8B5A3C" strokeWidth="2" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Therapeutic Intelligence</h3>
                        <p className={styles.featureDescription}>
                            Built on evidence-based therapeutic principles to provide supportive, empathetic guidance.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <rect x="10" y="14" width="20" height="28" rx="3" stroke="#8B5A3C" strokeWidth="2.5"/>
                                <rect x="14" y="18" width="12" height="2" rx="1" fill="#8B5A3C"/>
                                <rect x="14" y="24" width="12" height="2" rx="1" fill="#8B5A3C"/>
                                <rect x="14" y="30" width="8" height="2" rx="1" fill="#8B5A3C"/>
                                <path d="M30 10H34C36.2 10 38 11.8 38 14V34C38 36.2 36.2 38 34 38H30" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Multiple Access Points</h3>
                        <p className={styles.featureDescription}>
                            Access your support system anytime, anywhere through web, mobile, or desktop applications.
                        </p>
                    </div>
                    <div className={styles.featureCard}>
                        <div className={styles.featureIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M10 8C10 6.89543 10.8954 6 12 6H36C37.1046 6 38 6.89543 38 8V40C38 41.1046 37.1046 42 36 42H12C10.8954 42 10 41.1046 10 40V8Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinejoin="round"/>
                                <path d="M28 6V42" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M16 14H22" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M16 22H22" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.featureTitle}>Student Research</h3>
                        <p className={styles.featureDescription}>
                            Developed to explore the potential and challenges of AI in mental wellness support. Open to feedback.
                        </p>
                    </div>
                </div>
            </section>
            
            {/* How It Works Section */}
            <section id="how-it-works" className={styles.howItWorks}>
                <h2 className={styles.sectionTitle}>How It Works</h2>
                <div className={styles.stepsContainer}>
                    <div className={styles.step}>
                        <div className={styles.stepIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M12 20H36V38C36 39.1 35.1 40 34 40H14C12.9 40 12 39.1 12 38V20Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M16 20V12C16 9.8 17.8 8 20 8H28C30.2 8 32 9.8 32 12V20" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M24 28V32" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.stepTitle}>Sign In Securely</h3>
                        <p className={styles.stepDescription}>
                            Create your account with Google or continue as a guest. Your privacy is protected.
                        </p>
                    </div>
                    <div className={styles.stepConnector}>
                        <svg className={styles.arrowDesktop} width="48" height="24" viewBox="0 0 48 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 12H40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M36 8L40 12L36 16" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        <svg className={styles.arrowMobile} width="24" height="48" viewBox="0 0 24 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4L12 40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M8 36L12 40L16 36" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <div className={styles.step}>
                        <div className={styles.stepIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M8 16H40" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M8 32H40" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M16 8V24" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M32 24V40" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.stepTitle}>Set Preferences</h3>
                        <p className={styles.stepDescription}>
                            Choose your memory settings. You're in control of what Serena remembers.
                        </p>
                    </div>
                    <div className={styles.stepConnector}>
                        <svg className={styles.arrowDesktop} width="48" height="24" viewBox="0 0 48 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 12H40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M36 8L40 12L36 16" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        <svg className={styles.arrowMobile} width="24" height="48" viewBox="0 0 24 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4L12 40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M8 36L12 40L16 36" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <div className={styles.step}>
                        <div className={styles.stepIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M38 20H28L24 14L20 20H10C8.9 20 8 20.9 8 22V34C8 35.1 8.9 36 10 36H38C39.1 36 40 35.1 40 34V22C40 20.9 39.1 20 38 20Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.stepTitle}>Start Talking</h3>
                        <p className={styles.stepDescription}>
                            Share what's on your mind. Serena listens without judgment and responds with empathy.
                        </p>
                    </div>
                    <div className={styles.stepConnector}>
                        <svg className={styles.arrowDesktop} width="48" height="24" viewBox="0 0 48 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 12H40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M36 8L40 12L36 16" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        <svg className={styles.arrowMobile} width="24" height="48" viewBox="0 0 24 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4L12 40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M8 36L12 40L16 36" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <div className={styles.step}>
                        <div className={styles.stepIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M14 26C14 26 18 32 24 32C30 32 34 26 34 26" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M15 40H33C35.2 40 37 38.2 37 36V28C37 28 34 24 24 24C14 24 11 28 11 28V36C11 38.2 12.8 40 15 40Z" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M20 20C20 17.8 21.8 16 24 16C26.2 16 28 17.8 28 20" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M12 20C12 15.6 15.6 12 20 12" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                <path d="M36 20C36 15.6 32.4 12 28 12" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.stepTitle}>Memories Form</h3>
                        <p className={styles.stepDescription}>
                            Important details are remembered automatically, building a personalized understanding.
                        </p>
                    </div>
                    <div className={styles.stepConnector}>
                        <svg className={styles.arrowDesktop} width="48" height="24" viewBox="0 0 48 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 12H40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M36 8L40 12L36 16" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        <svg className={styles.arrowMobile} width="24" height="48" viewBox="0 0 24 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 4L12 40" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4"/>
                            <path d="M8 36L12 40L16 36" stroke="#C9B8AB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <div className={styles.step}>
                        <div className={styles.stepIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <path d="M34 24C34 29.5 29.5 34 24 34C18.5 34 14 29.5 14 24C14 18.5 18.5 14 24 14" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M24 14V10" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M24 38V34" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M34 24H38" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M10 24H14" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M31.1 16.9L33.9 14.1" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M14.1 33.9L16.9 31.1" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M31.1 31.1L33.9 33.9" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                                <path d="M14.1 14.1L16.9 16.9" stroke="#8B5A3C" strokeWidth="2.5" strokeLinecap="round"/>
                            </svg>
                        </div>
                        <h3 className={styles.stepTitle}>Continuous Support</h3>
                        <p className={styles.stepDescription}>
                            Every conversation builds on the last, providing increasingly personalized and meaningful support.
                        </p>
                    </div>
                </div>
            </section>
            
            {/* Technology Section */}
            <section id="technology" className={styles.technology}>
                <h2 className={styles.sectionTitle}>Powered by Advanced Technology</h2>
                <p className={styles.sectionSubtitle}>
                    Built with a production-grade, scalable, and secure technology stack.
                </p>
                <div className={styles.logoGrid}>
                    <div className={styles.logoCard}>
                        <img src="/logos/Vertex-AI.svg" alt="Google Cloud Vertex AI Logo" className={styles.logoImage} />
                        <span className={styles.logoName}>Vertex AI</span>
                    </div>
                    <div className={styles.logoCard}>
                        <img src="/logos/google-gemini.svg" alt="Google Gemini Logo" className={styles.logoImage} />
                        <span className={styles.logoName}>Gemini 1.5 Flash</span>
                    </div>
                    <div className={styles.logoCard}>
                        <img src="/logos/firebase.svg" alt="Firebase Logo" className={styles.logoImage} />
                        <span className={styles.logoName}>Firebase Auth</span>
                    </div>
                    <div className={styles.logoCard}>
                        <img src="/logos/Firestore.svg" alt="Google Firestore Logo" className={styles.logoImage} />
                        <span className={styles.logoName}>Firestore</span>
                    </div>
                    <div className={styles.logoCard}>
                        <img src="/logos/reactjs.svg" alt="React Logo" className={styles.logoImage} />
                        <span className={styles.logoName}>React</span>
                    </div>
                    <div className={styles.logoCard}>
                        <img src="/logos/data-encryption.svg" alt="Data Encryption Icon" className={styles.logoImage} />
                        <span className={styles.logoName}>KMS Encryption</span>
                    </div>
                </div>
            </section>

            {/* About Section */}
            <section className={styles.aboutSection} id="about">
                <h2 className={styles.sectionTitle}>Who Is Serena For?</h2>
                <h3 className={styles.aboutHeading}>
                    For People Who Want to Be Heard, Not Fixed
                </h3>
                
                <div className={styles.aboutListContainer}>
                    {/* Item 1: Vent */}
                    <article className={styles.aboutItem}>
                        <div className={styles.aboutIconWrapper}>
                            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <div className={styles.aboutTextWrapper}>
                            <h4 className={styles.aboutItemTitle}>The Person Who Needs to Vent</h4>
                            <p className={styles.aboutItemText}>Sometimes you just need someone to listen. Serena does that without making it weird.</p>
                        </div>
                    </article>

                    {/* Item 2: Figuring Things Out */}
                    <article className={`${styles.aboutItem} ${styles.aboutItemReverse}`}>
                        <div className={styles.aboutTextWrapper}>
                            <h4 className={styles.aboutItemTitle}>The Person Figuring Things Out</h4>
                            <p className={styles.aboutItemText}>You don't need advice. You need clarity. Serena helps you see your own thoughts more clearly.</p>
                        </div>
                        <div className={styles.aboutIconWrapper}>
                            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M9.5 2.2a2.5 2.5 0 0 1 5 0v1.7a0.5 0.5 0 0 0 .5.5h1.7a2.5 2.5 0 0 1 0 5h-1.7a0.5 0.5 0 0 0-.5.5v1.7a2.5 2.5 0 0 1-5 0v-1.7a0.5 0.5 0 0 0-.5-.5h-1.7a2.5 2.5 0 0 1 0-5h1.7a0.5 0.5 0 0 0 .5-.5v-1.7z" />
                                <path d="M6 16.5a2.5 2.5 0 0 1 5 0v1.7a0.5 0.5 0 0 0 .5.5h1.7a2.5 2.5 0 0 1 0 5h-1.7a0.5 0.5 0 0 0-.5.5v1.7a2.5 2.5 0 0 1-5 0v-1.7a0.5 0.5 0 0 0-.5-.5h-1.7a2.5 2.5 0 0 1 0-5h1.7a0.5 0.5 0 0 0 .5-.5v-1.7z" />
                            </svg>
                        </div>
                    </article>

                    {/* Item 3: Privacy */}
                    <article className={styles.aboutItem}>
                        <div className={styles.aboutIconWrapper}>
                            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                        </div>
                        <div className={styles.aboutTextWrapper}>
                            <h4 className={styles.aboutItemTitle}>The Person Who Values Privacy</h4>
                            <p className={styles.aboutItemText}>You're not ready for a therapist. You're not comfortable with generic AI. You need something human-centered and secure.</p>
                        </div>
                    </article>
                    
                    {/* Item 4: Resilience */}
                    <article className={`${styles.aboutItem} ${styles.aboutItemReverse}`}>
                        <div className={styles.aboutTextWrapper}>
                            <h4 className={styles.aboutItemTitle}>The Person Building Mental Resilience</h4>
                            <p className={styles.aboutItemText}>You want continuous support that actually remembers you and meets you where you are.</p>
                        </div>
                        <div className={styles.aboutIconWrapper}>
                             <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </div>
                    </article>
                </div>

                <div className={styles.aboutDisclaimer}>
                    <h4 className={styles.aboutDisclaimerTitle}>Not a Replacement For:</h4>
                    <p className={styles.aboutDisclaimerText}>
                        Professional therapy, crisis intervention, or medical diagnosis. Serena is a supportive companion designed to complement—not replace—human care. If you're in crisis, please reach out to a mental health professional.
                    </p>
                </div>
            </section>

            {/* Comparison Section */}
            <section className={styles.comparisonSection} id="comparison">
                <h2 className={styles.sectionTitle}>Why Choose Serena?</h2>
                
                <div className={styles.comparisonTable}>
                    <table>
                        <thead>
                            <tr>
                                <th>Aspect</th>
                                <th>Generic Chatbots</th>
                                <th>Serena</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Conversation Style</td>
                                <td>Interrogation</td>
                                <td>Supportive listening</td>
                            </tr>
                            <tr>
                                <td>Memory</td>
                                <td>Forgets or remembers everything</td>
                                <td>Intelligently curates</td>
                            </tr>
                            <tr>
                                <td>Speed</td>
                                <td>Slow with large memory</td>
                                <td>Sub-100ms retrieval</td>
                            </tr>
                            <tr>
                                <td>Privacy</td>
                                <td>Often unclear</td>
                                <td>Explicit, encrypted, user-controlled</td>
                            </tr>
                            <tr>
                                <td>Therapeutic Approach</td>
                                <td>Generic responses</td>
                                <td>TTM/CBT framework</td>
                            </tr>
                            <tr>
                                <td>Goal</td>
                                <td>Appear helpful</td>
                                <td>Help YOU be helpful to yourself</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            {/* FAQ Section */}
            <section className={styles.faqSection} id="faq">
                <h2 className={styles.sectionTitle}>FAQs</h2>
                
                <div className={styles.faqContainer}>
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            Is My Data Really Private?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            Yes. All conversations are encrypted with military-grade security. Serena only stores summaries of meaningful moments—not a transcript of everything you say. You control what gets saved.
                        </p>
                    </details>
                    
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            Can Serena Replace My Therapist?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            No. Serena is a supportive companion designed to complement—not replace—professional mental health care. She's there for the moments between therapy, the late-night thoughts, or when you just need to be heard.
                        </p>
                    </details>
                    
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            What Makes the Memory System Different?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            Most chatbots either forget everything or remember everything indiscriminately. Serena intelligently curates what matters using Vertex AI Vector Search. She remembers the significant moments—the breakthroughs, the challenges, the patterns. Not the noise.
                        </p>
                    </details>
                    
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            Will Serena Judge Me?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            Never. Serena is designed to listen without judgment using CBT principles. Your thoughts, feelings, and experiences are valid. She's here to help you process them—not criticize them.
                        </p>
                    </details>
                    
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            Can I Delete Everything?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            Absolutely. You can delete all memories with one click, reset your instructions, and start fresh anytime. Your data is yours to control.
                        </p>
                    </details>
                    
                    <details className={styles.faqItem}>
                        <summary className={styles.faqQuestion}>
                            Is Serena Available in My Language?
                            <span className={styles.faqIcon}>+</span>
                        </summary>
                        <p className={styles.faqAnswer}>
                            Yes! Serena is multilingual and automatically responds in whatever language you use. Your conversation should feel natural in your preferred language.
                        </p>
                    </details>
                </div>
            </section>

            

            {/* Footer */}
            <footer className={styles.footer}>
                {/* Crisis Resources */}
                <div className={styles.crisisSection}>
                    <h3 className={styles.crisisTitle}>
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{flexShrink: 0}}>
                            <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2"/>
                            <path d="M10 6V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                            <circle cx="10" cy="14" r="1" fill="currentColor"/>
                        </svg>
                        Important
                    </h3>
                    <p className={styles.crisisText}>
                        Serena is a supportive companion for mental health conversations, not a crisis service. 
                        If you're in crisis or having thoughts of self-harm, please contact <strong>your local crisis hotline</strong> or 
                        text <strong>HOME to 741741</strong> (Crisis Text Line).
                    </p>
                </div>

                <div className={styles.footerContent}>
                    <div className={styles.footerBrand}>
                        <img src="/logoS.png" alt="Serena Logo" className={styles.footerLogo} loading="lazy" />
                        <span className={styles.brandName}>Serena</span>
                        <p className={styles.footerTagline}>Mental health support that remembers</p>
                    </div>
                    <div className={styles.footerLinks}>
                        <a href="#" className={styles.footerLink}>Contact Us</a>
                    </div>
                </div>
                <div className={styles.footerBottom}>
                    <p>A Student Research Project</p>
                    <p>&copy; 2025 Serena. All rights reserved.</p>
                </div>
            </footer>
        </main>
    );
}
import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/ibm-plex-sans-arabic/400.css';
import '@fontsource/ibm-plex-sans-arabic/500.css';
import '@fontsource/ibm-plex-sans-arabic/600.css';
import '@fontsource/ibm-plex-sans-arabic/700.css';
import App from './App';
import './styles.css';
import './public.css';

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);

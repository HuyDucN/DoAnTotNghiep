import React from 'react'
import ReactDOM from 'react-dom/client'
import SessionQueryProvider from './components/SessionQueryProvider'
import App from './App.tsx'
import './styles/global.css'
import './styles/light-theme.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SessionQueryProvider>
      <App />
    </SessionQueryProvider>
  </React.StrictMode>,
)

import { useState, useRef } from 'react'

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Welcome to Power BI Chat! Please upload a .pbix dashboard to get started.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dashboardLoaded, setDashboardLoaded] = useState(false)
  
  const fileInputRef = useRef(null)

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.pbix')) {
      alert('Please upload a .pbix file')
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      })
      
      if (!res.ok) throw new Error('Upload failed')
      
      setDashboardLoaded(true)
      setMessages(prev => [...prev, { role: 'ai', content: `Successfully loaded ${file.name}! What would you like to know about it?` }])
    } catch (err) {
      alert('Error uploading file: ' + err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading || !dashboardLoaded) return

    const question = input
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      })

      if (!res.ok) throw new Error('Chat failed')
      const data = await res.json()

      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: data.answer,
        sql: data.sql,
        rows: data.rows
      }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I encountered an error answering that.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar for Upload */}
      <div className="sidebar glass-panel">
        <h2>Power BI Chat</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Ask questions about your data using natural language.
        </p>

        <div 
          className="upload-zone" 
          onClick={() => !uploading && fileInputRef.current.click()}
        >
          {uploading ? (
            <div>
              <div className="spinner" style={{ marginBottom: '1rem' }}></div>
              <p>Extracting data...<br/><small style={{color:'var(--text-muted)'}}>(This takes ~30s)</small></p>
            </div>
          ) : (
            <div>
              <span style={{ fontSize: '2rem' }}>📊</span>
              <h3>Upload Dashboard</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Click to select a .pbix file</p>
            </div>
          )}
          <input 
            type="file" 
            ref={fileInputRef} 
            accept=".pbix" 
            onChange={handleUpload} 
            disabled={uploading}
          />
        </div>

        {dashboardLoaded && (
          <div style={{ marginTop: 'auto', padding: '1rem', background: 'rgba(74, 222, 128, 0.1)', borderRadius: '8px', border: '1px solid rgba(74, 222, 128, 0.2)' }}>
            <span style={{ color: '#4ade80' }}>✓ Dashboard Active</span>
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="main-content glass-panel">
        <div className="messages-container">
          {messages.map((msg, i) => (
            <Message key={i} msg={msg} />
          ))}
          {loading && (
            <div className="message ai">
              <div className="spinner"></div>
            </div>
          )}
        </div>

        <form className="input-area" onSubmit={handleSend}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={dashboardLoaded ? "Ask a question..." : "Please upload a dashboard first"}
            disabled={!dashboardLoaded || loading}
          />
          <button type="submit" disabled={!input.trim() || !dashboardLoaded || loading}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

function Message({ msg }) {
  const [showSql, setShowSql] = useState(false)

  return (
    <div className={`message ${msg.role}`}>
      <div>{msg.content}</div>
      
      {msg.sql && (
        <>
          <button className="sql-toggle" onClick={() => setShowSql(!showSql)}>
            {showSql ? 'Hide SQL' : 'View SQL'}
          </button>
          {showSql && (
            <div className="sql-block">
              {msg.sql}
              {msg.rows && msg.rows.length > 0 && (
                <table style={{ marginTop: '1rem', width: '100%' }}>
                  <thead>
                    <tr>
                      {Object.keys(msg.rows[0]).map(k => <th key={k}>{k}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {msg.rows.map((r, i) => (
                      <tr key={i}>
                        {Object.values(r).map((v, j) => <td key={j}>{v?.toString() || 'null'}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App

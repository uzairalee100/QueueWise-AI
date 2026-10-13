/**
 * QueueWise AI — Operations Advisor (AI Agent UI)
 *
 * Grounded natural language operations assistant for supervisors:
 * - Direct queries against live database state (counters, queues, analytics)
 * - Zero hallucination guaranteed: citations and metrics metadata disclosed
 * - Multilingual support (English & Urdu)
 * - Quick prompt chips and action shortcuts
 */
import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'
import { askAgent, getAgentCapabilities } from '../services/api'
import type { AgentResponse, AgentCapabilitiesResponse } from '../types/api'

interface ChatMessage {
  id: string
  sender: 'user' | 'agent'
  text: string
  textUr?: string | null
  intent?: string
  grounding?: {
    source: string
    timestamp: string
    metrics_cited: string[]
  }
  data?: Record<string, unknown>
  agentMode?: string
  llmProvider?: string
  timestamp: Date
}

export function AgentPage() {
  const { lang, t, isRTL } = useLanguage()

  // State
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [capabilities, setCapabilities] = useState<AgentCapabilitiesResponse | null>(null)
  const [expandedGroundingId, setExpandedGroundingId] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Initial load: capabilities and initial greeting
  useEffect(() => {
    // Fetch capabilities
    getAgentCapabilities()
      .then((caps) => {
        setCapabilities(caps)
      })
      .catch((err) => {
        console.warn('Failed to load agent capabilities:', err)
      })

    // Seed default welcome message
    const welcomeEn =
      "Hello! I am your QueueWise AI Operations Advisor. I can analyze live waiting queues, detect bottlenecks, recommend optimal counter staffing, and provide SLA performance metrics—grounded directly in your live system data with zero hallucinations. How can I help you manage operations right now?"
    const welcomeUr =
      "السلام علیکم! میں کیو وائز اے آئی آپریشنز مشیر ہوں۔ میں لائیو قطاروں، ممکنہ رکاوٹوں، کاؤنٹرز کی بہترین تقسیم اور کارکردگی کا تجزیہ کر کے حقیقی ڈیٹا پر مبنی مصدقہ مشورہ دے سکتا ہوں۔ آپ کس بارے میں معلومات حاصل کرنا چاہتے ہیں؟"

    setMessages([
      {
        id: 'msg-welcome',
        sender: 'agent',
        text: welcomeEn,
        textUr: welcomeUr,
        intent: 'greeting',
        grounding: {
          source: 'QueueWise AI Operations Engine',
          timestamp: new Date().toISOString(),
          metrics_cited: ['zero_hallucination', 'live_db_telemetry'],
        },
        agentMode: 'rule_based',
        llmProvider: 'none',
        timestamp: new Date(),
      },
    ])
  }, [])

  // Submit Query
  const handleSendQuery = async (queryText?: string) => {
    const textToSend = (queryText ?? inputText).trim()
    if (!textToSend || loading) return

    setInputText('')

    // Append user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const response: AgentResponse = await askAgent({
        query: textToSend,
        language: lang,
        sessionId: 'default',
      })

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        text: response.response,
        textUr: response.response_ur,
        intent: response.intent,
        grounding: response.grounding,
        data: response.data,
        agentMode: response.agent_mode,
        llmProvider: response.llm_provider,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, agentMsg])
    } catch (err) {
      console.error('Agent query error:', err)
      const errorMsg: ChatMessage = {
        id: `agent-err-${Date.now()}`,
        sender: 'agent',
        text: 'Sorry, I encountered an issue analyzing the current queue state. Please verify the system connectivity and try again.',
        textUr: 'معذرت، لائیو سسٹم کا ڈیٹا حاصل کرنے میں دشواری پیش آئی۔ براہ کرم دوبارہ کوشش کریں۔',
        intent: 'error',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  // Clear Chat
  const handleClearChat = () => {
    setMessages([])
  }

  // Suggested Prompts
  const suggestedPrompts = [
    {
      icon: '📊',
      label: t.queryStatus,
      query: lang === 'ur' ? 'قطار کی موجودہ صورتحال کیا ہے؟' : 'What is the current queue status?',
    },
    {
      icon: '⚠️',
      label: t.queryBottlenecks,
      query: lang === 'ur' ? 'کیا ابھی کوئی مسئلہ یا تاخیر ہے؟' : 'Are there any bottlenecks right now?',
    },
    {
      icon: '🪑',
      label: t.queryCounters,
      query: lang === 'ur' ? 'کاؤنٹرز کو کیسے تقسیم کریں؟' : 'How should we allocate counters?',
    },
    {
      icon: '⏱️',
      label: t.querySLA,
      query: lang === 'ur' ? 'معیاری وقت اور کارکردگی کے اعداد و شمار کیا ہیں؟' : 'What is the SLA compliance and wait time report?',
    },
    {
      icon: '🏢',
      label: t.queryServices,
      query: lang === 'ur' ? 'تمام سروسز کی کارکردگی کیسی ہے؟' : 'How is each service performing?',
    },
  ]

  return (
    <div className={`max-w-6xl mx-auto px-4 py-6 sm:px-6 flex flex-col gap-6 ${isRTL ? 'font-urdu' : ''}`}>
      {/* Top Banner Header */}
      <div className="glass rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 border border-white/10 shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-accent-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-start sm:items-center gap-4 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-500 via-primary-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-accent-500/20 shrink-0">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                {t.aiAdvisor}
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-success-500/20 text-success-300 border border-success-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
                {t.ruleBasedGrounded}
              </span>
            </div>
            <p className="text-surface-200/70 text-sm mt-1">
              {t.aiAdvisorSubtitle}
            </p>
          </div>
        </div>

        {/* Header Action Badges */}
        <div className="flex flex-wrap items-center gap-2 relative z-10">
          <div className="glass-light px-3 py-1.5 rounded-xl border border-white/10 text-xs text-surface-200/80 flex items-center gap-2">
            <span className="text-surface-200/50">{t.executionMode}:</span>
            <span className="font-semibold text-accent-300">
              {capabilities?.agent_mode || 'rule_based'}
            </span>
          </div>
          <button
            type="button"
            onClick={handleClearChat}
            className="px-3 py-1.5 rounded-xl glass-light border border-white/10 hover:border-white/20 text-xs font-semibold text-surface-200/70 hover:text-white transition-all cursor-pointer flex items-center gap-1.5"
            title={t.clearChat}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span>{t.clearChat}</span>
          </button>
        </div>
      </div>

      {/* Suggested Quick Prompt Chips */}
      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold text-surface-200/60 uppercase tracking-wider px-1">
          {t.suggestedQueries}
        </span>
        <div className="flex flex-wrap gap-2">
          {suggestedPrompts.map((p, idx) => (
            <button
              key={idx}
              type="button"
              disabled={loading}
              onClick={() => handleSendQuery(p.query)}
              className="glass px-3.5 py-2 rounded-xl border border-white/10 hover:border-accent-500/40 hover:bg-white/5 text-xs font-medium text-surface-200 hover:text-white transition-all flex items-center gap-2 group cursor-pointer shadow-sm hover:shadow-accent-500/10 active:scale-95"
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Conversation Stream */}
      <div className="glass rounded-3xl p-4 sm:p-6 min-h-[460px] flex flex-col justify-between border border-white/10 shadow-xl">
        <div className="flex flex-col gap-4 overflow-y-auto max-h-[560px] pr-1">
          {messages.map((msg) => {
            const isUser = msg.sender === 'user'

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-full`}
              >
                {/* Message Bubble Container */}
                <div
                  className={`max-w-[92%] sm:max-w-[80%] rounded-2xl p-4.5 transition-all shadow-md ${
                    isUser
                      ? 'bg-gradient-to-br from-primary-600 to-indigo-700 text-white border border-primary-400/20 rounded-tr-sm'
                      : 'glass-light border border-white/10 text-surface-100 rounded-tl-sm'
                  }`}
                >
                  {/* Sender Header */}
                  <div className="flex items-center justify-between gap-3 mb-2 pb-1.5 border-b border-white/10 text-xs">
                    <div className="flex items-center gap-1.5">
                      {isUser ? (
                        <>
                          <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-[10px] font-bold">
                            U
                          </div>
                          <span className="font-semibold text-white/90">Supervisor</span>
                        </>
                      ) : (
                        <>
                          <div className="w-5 h-5 rounded-full bg-accent-500/30 text-accent-300 flex items-center justify-center text-[10px] font-bold">
                            AI
                          </div>
                          <span className="font-semibold text-accent-300">QueueWise Advisor</span>
                          {msg.intent && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-white/5 text-surface-200/80 border border-white/10">
                              intent: {msg.intent}
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Message Body Content */}
                  <div className="text-sm sm:text-base leading-relaxed whitespace-pre-line">
                    {lang === 'ur' && msg.textUr ? msg.textUr : msg.text}
                  </div>

                  {/* Grounding Metadata Drawer (Only for Agent messages with grounding) */}
                  {!isUser && msg.grounding && (
                    <div className="mt-4 pt-3 border-t border-white/10 flex flex-col gap-2">
                      <div className="flex items-center justify-between gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedGroundingId(
                              expandedGroundingId === msg.id ? null : msg.id
                            )
                          }
                          className="text-[11px] font-semibold text-accent-400 hover:text-accent-300 flex items-center gap-1 cursor-pointer"
                        >
                          <svg
                            className={`w-3.5 h-3.5 transition-transform ${
                              expandedGroundingId === msg.id ? 'rotate-90' : ''
                            }`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                          </svg>
                          <span>{t.groundingEvidence}</span>
                        </button>

                        {/* Cited Metrics Chips */}
                        {msg.grounding.metrics_cited && msg.grounding.metrics_cited.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1">
                            {msg.grounding.metrics_cited.slice(0, 3).map((metric, mIdx) => (
                              <span
                                key={mIdx}
                                className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-white/5 text-surface-200/70 border border-white/5"
                              >
                                {metric}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Expanded Evidence Drawer Details */}
                      {expandedGroundingId === msg.id && (
                        <div className="glass rounded-xl p-3 border border-white/10 text-xs flex flex-col gap-2 mt-1">
                          <div className="flex items-center justify-between text-surface-200/70">
                            <span>{t.evidenceSource}:</span>
                            <span className="font-mono text-white/90">{msg.grounding.source}</span>
                          </div>
                          <div className="flex items-center justify-between text-surface-200/70">
                            <span>{t.timestampLabel}:</span>
                            <span className="font-mono text-white/90">
                              {new Date(msg.grounding.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          {msg.grounding.metrics_cited && msg.grounding.metrics_cited.length > 0 && (
                            <div>
                              <span className="text-surface-200/70 block mb-1">{t.citedMetrics}:</span>
                              <div className="flex flex-wrap gap-1">
                                {msg.grounding.metrics_cited.map((m, mIdx) => (
                                  <span
                                    key={mIdx}
                                    className="px-2 py-0.5 rounded bg-accent-500/10 text-accent-300 font-mono text-[10px] border border-accent-500/20"
                                  >
                                    {m}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Action Shortcuts */}
                          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-white/5">
                            <Link
                              to="/staff"
                              className="px-2.5 py-1 rounded-lg bg-primary-500/20 text-primary-300 hover:bg-primary-500/30 transition-colors text-[11px] font-medium flex items-center gap-1"
                            >
                              <span>🪑</span>
                              <span>{t.jumpToCounters}</span>
                            </Link>
                            <Link
                              to="/simulation"
                              className="px-2.5 py-1 rounded-lg bg-accent-500/20 text-accent-300 hover:bg-accent-500/30 transition-colors text-[11px] font-medium flex items-center gap-1"
                            >
                              <span>🧪</span>
                              <span>{t.jumpToSimLab}</span>
                            </Link>
                            <Link
                              to="/analytics"
                              className="px-2.5 py-1 rounded-lg bg-white/10 text-surface-100 hover:bg-white/15 transition-colors text-[11px] font-medium flex items-center gap-1"
                            >
                              <span>📈</span>
                              <span>{t.jumpToAnalytics}</span>
                            </Link>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className="text-[10px] text-surface-200/40 mt-2 text-right">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-start gap-3 max-w-[80%]">
              <div className="glass-light rounded-2xl rounded-tl-sm p-4 border border-white/10 flex items-center gap-3">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" />
                </div>
                <span className="text-xs font-medium text-surface-200/80">
                  {t.agentThinking}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="mt-4 pt-3 border-t border-white/10">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendQuery()
            }}
            className="flex items-center gap-2"
          >


            {/* Natural language query input */}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={t.askAgentPrompt}
              disabled={loading}
              className="flex-1 bg-surface-900/60 border border-white/10 focus:border-accent-500/60 rounded-2xl px-4 py-3 text-sm text-white placeholder-surface-200/40 focus:outline-none focus:ring-2 focus:ring-accent-500/20 transition-all shadow-inner"
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!inputText.trim() || loading}
              className="px-5 py-3 rounded-2xl bg-gradient-to-r from-accent-500 to-primary-600 hover:from-accent-400 hover:to-primary-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-sm shadow-lg shadow-accent-500/20 transition-all flex items-center gap-2 cursor-pointer shrink-0 active:scale-95"
            >
              <span>{t.askButton}</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

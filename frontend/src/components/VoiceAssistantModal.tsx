/**
 * QueueWise AI — Multilingual Voice Assistant Modal
 *
 * Provides a bilingual voice interface for citizens and staff:
 * - Speech-to-Text input in English, Native Urdu, and Roman Urdu
 * - Connects to /api/v1/voice/query endpoint
 * - Auto-plays spoken audio responses via Web Speech API Text-to-Speech
 * - Includes sound effect chimes and standard low-literacy broadcast previews
 */
import { useState, useRef, useEffect } from 'react'
import { useLanguage } from '../context/LanguageContext'
import { processVoiceQuery } from '../services/api'
import { speakText, stopSpeech, playCallChime, playApproachingAlert } from '../utils/audio'
import type { VoiceQueryResponse } from '../types/api'

interface VoiceAssistantModalProps {
  isOpen: boolean
  onClose: () => void
  initialTokenId?: string
}

export function VoiceAssistantModal({ isOpen, onClose, initialTokenId }: VoiceAssistantModalProps) {
  const { lang, isRTL } = useLanguage()

  const [queryText, setQueryText] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<VoiceQueryResponse | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  const recognitionRef = useRef<unknown>(null)

  // Clear query on open
  useEffect(() => {
    if (isOpen) {
      setQueryText('')
      setResponse(null)
    } else {
      stopSpeech()
      if (recognitionRef.current) {
        (recognitionRef.current as { stop: () => void }).stop()
      }
      setIsListening(false)
      setIsSpeaking(false)
    }
  }, [isOpen])

  // Toggle Microphone (Speech-to-Text)
  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        (recognitionRef.current as { stop: () => void }).stop()
      }
      setIsListening(false)
      return
    }

    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: new () => unknown; webkitSpeechRecognition?: new () => unknown })
        .SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => unknown }).webkitSpeechRecognition

    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. You can type your question below.')
      return
    }

    try {
      const recognition = new SpeechRecognition() as {
        continuous: boolean
        interimResults: boolean
        lang: string
        onresult: (e: { results: Array<Array<{ transcript: string }>> }) => void
        onerror: () => void
        onend: () => void
        start: () => void
      }
      recognitionRef.current = recognition
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = lang === 'ur' ? 'ur-PK' : 'en-US'

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        if (transcript) {
          setQueryText(transcript)
          handleSendVoiceQuery(transcript)
        }
      }

      recognition.onerror = () => setIsListening(false)
      recognition.onend = () => setIsListening(false)

      recognition.start()
      setIsListening(true)
    } catch (err) {
      console.warn('Speech recognition start failed:', err)
      setIsListening(false)
    }
  }

  // Handle Query Submission
  const handleSendVoiceQuery = async (overrideText?: string) => {
    const textToSend = (overrideText ?? queryText).trim()
    if (!textToSend || loading) return

    setLoading(true)
    try {
      const result = await processVoiceQuery({
        query: textToSend,
        token_identifier: initialTokenId,
        session_id: 'default',
      })
      setResponse(result)

      // Play chime if appropriate
      if (result.chime_hint === 'turn_called') {
        playCallChime()
      } else if (result.chime_hint === 'approaching') {
        playApproachingAlert()
      }

      // Auto-read aloud in appropriate language
      setIsSpeaking(true)
      const speechLang = result.detected_language === 'ur' ? 'ur' : 'en'
      speakText(result.spoken_text, speechLang)

      setTimeout(() => {
        setIsSpeaking(false)
      }, 4000)
    } catch (err) {
      console.error('Voice query failed:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className={`glass max-w-lg w-full rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative overflow-hidden flex flex-col gap-5 ${isRTL ? 'font-urdu' : ''}`}>
        {/* Glow backdrop */}
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-accent-500/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-64 h-64 bg-primary-500/15 rounded-full blur-3xl pointer-events-none" />

        {/* Modal Header */}
        <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-accent-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-accent-500/20">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>{lang === 'ur' ? 'صوتی معاون' : 'Voice Assistant'}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-500/20 text-accent-300 border border-accent-500/30">
                  Bilingual TTS
                </span>
              </h2>
              <p className="text-xs text-surface-200/60">
                {lang === 'ur' ? 'بول کر یا لکھ کر اپنا ٹوکن معلوم کریں' : 'Speak or type in English, Urdu, or Roman Urdu'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-9 h-9 rounded-xl glass-light border border-white/10 hover:border-white/20 text-surface-200 hover:text-white flex items-center justify-center cursor-pointer transition-colors"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Microphone Wave Centerpiece */}
        <div className="flex flex-col items-center justify-center py-4 relative z-10">
          <button
            type="button"
            onClick={toggleListening}
            className={`w-20 h-20 rounded-3xl flex items-center justify-center transition-all cursor-pointer shadow-2xl relative ${
              isListening
                ? 'bg-rose-500 text-white shadow-rose-500/50 scale-105 animate-pulse border-2 border-rose-300'
                : 'bg-gradient-to-br from-accent-500 to-primary-600 text-white hover:scale-105 border border-white/20 shadow-accent-500/30 active:scale-95'
            }`}
            title={isListening ? 'Listening... Tap to stop' : 'Tap to Speak'}
            aria-label="Toggle Microphone"
          >
            {isListening ? (
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-6 bg-white rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-8 bg-white rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-6 bg-white rounded-full animate-bounce" />
              </div>
            ) : (
              <svg className="w-9 h-9" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            )}
          </button>
          <span className="text-xs font-semibold mt-3 text-surface-200/80">
            {isListening
              ? lang === 'ur' ? 'سن رہا ہے... بولیں' : 'Listening... Speak now'
              : lang === 'ur' ? 'بولنے کے لیے مائیک دبائیں' : 'Tap microphone to speak'}
          </span>
        </div>

        {/* Sample Voice Prompts */}
        <div className="flex flex-wrap gap-1.5 justify-center relative z-10">
          {[
            { label: 'Mera token kab aayega?', text: 'Mera token kab aayega?' },
            { label: 'Kitne log agay hain?', text: 'Kitne log mere agay hain?' },
            { label: 'How long is the wait?', text: 'How long is the wait?' },
            { label: 'Naya token chahiye', text: 'Naya token kaise milega?' },
          ].map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setQueryText(prompt.text)
                handleSendVoiceQuery(prompt.text)
              }}
              className="px-2.5 py-1 rounded-lg glass-light border border-white/5 hover:border-white/20 text-[11px] text-surface-200/70 hover:text-white transition-all cursor-pointer"
            >
              {prompt.label}
            </button>
          ))}
        </div>

        {/* Response Display Box */}
        {response && (
          <div className="glass-light rounded-2xl p-4 border border-accent-500/30 flex flex-col gap-2 relative z-10 animate-slide-up">
            <div className="flex items-center justify-between text-xs text-surface-200/60 pb-1.5 border-b border-white/10">
              <span className="font-semibold text-accent-300">
                {lang === 'ur' ? 'جواب' : 'Spoken Response'}
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsSpeaking(true)
                  speakText(response.spoken_text, response.detected_language === 'ur' ? 'ur' : 'en')
                  setTimeout(() => setIsSpeaking(false), 4000)
                }}
                className={`text-[11px] flex items-center gap-1 cursor-pointer transition-colors ${
                  isSpeaking ? 'text-accent-300 animate-pulse font-bold' : 'text-accent-400 hover:text-accent-300'
                }`}
              >
                🔊 <span>{isSpeaking ? (lang === 'ur' ? 'آواز جاری ہے...' : 'Speaking...') : (lang === 'ur' ? 'دوبارہ سنیں' : 'Replay Audio')}</span>
              </button>
            </div>

            <p className="text-sm sm:text-base font-medium text-white leading-relaxed">
              {response.spoken_text}
            </p>

            {response.spoken_text_roman && response.detected_language === 'ur' && (
              <p className="text-xs text-surface-200/60 italic font-mono">
                {response.spoken_text_roman}
              </p>
            )}

            {response.metadata && typeof response.metadata.position !== 'undefined' && (
              <div className="flex items-center gap-3 pt-2 text-xs border-t border-white/5 text-surface-200/80">
                <span>Position: <strong className="text-white">{String(response.metadata.position)}</strong></span>
                <span>People Ahead: <strong className="text-white">{String(response.metadata.people_ahead ?? 0)}</strong></span>
                <span>Wait: <strong className="text-white">{String(response.metadata.estimated_wait_minutes ?? 1)} min</strong></span>
              </div>
            )}
          </div>
        )}

        {/* Typed Input Field Fallback */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendVoiceQuery()
          }}
          className="flex items-center gap-2 pt-2 border-t border-white/10 relative z-10"
        >
          <input
            type="text"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder={lang === 'ur' ? 'یا سوال یہاں لکھیں...' : 'Or type query here...'}
            disabled={loading}
            className="flex-1 bg-surface-900/60 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white placeholder-surface-200/40 focus:outline-none focus:ring-1 focus:ring-accent-500/40"
          />
          <button
            type="submit"
            disabled={!queryText.trim() || loading}
            className="px-4 py-2.5 rounded-xl bg-accent-500 hover:bg-accent-400 disabled:opacity-40 text-white font-bold text-xs cursor-pointer transition-all"
          >
            {loading ? '...' : (lang === 'ur' ? 'بھیجیں' : 'Ask')}
          </button>
        </form>
      </div>
    </div>
  )
}

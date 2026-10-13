/**
 * QueueWise AI — Language Context Provider
 *
 * Manages active language state ('en' | 'ur') and provides translation strings.
 */
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { translations, type Language } from '../i18n/translations'

interface LanguageContextType {
  lang: Language
  setLang: (lang: Language) => void
  toggleLang: () => void
  t: typeof translations.en
  isRTL: boolean
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

const STORAGE_KEY = 'queuewise_language'

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'ur' ? 'ur' : 'en'
  })

  const setLang = (newLang: Language) => {
    setLangState(newLang)
    localStorage.setItem(STORAGE_KEY, newLang)
  }

  const toggleLang = () => {
    setLang(lang === 'en' ? 'ur' : 'en')
  }

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ur' ? 'rtl' : 'ltr'
  }, [lang])

  const value: LanguageContextType = {
    lang,
    setLang,
    toggleLang,
    t: translations[lang],
    isRTL: lang === 'ur',
  }

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}

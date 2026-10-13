/**
 * QueueWise AI — Simulation Lab & Counter Allocation Optimizer
 *
 * Full-featured interactive simulation suite:
 *  - 6 Preset Challenge Scenarios (A–F)
 *  - Deterministic Discrete-Event Queue Simulator with RNG seeding
 *  - Dynamic Wait Estimator Fidelity (Estimate vs Actual comparison)
 *  - M/M/c Algorithmic Counter Allocation Optimizer
 *  - One-click "Test Optimized Allocation" re-simulation
 *  - Bilingual English/Urdu interface
 */
import { useState, useEffect } from 'react'
import { useLanguage } from '../context/LanguageContext'
import {
  getScenarios,
  runSimulation,
  optimizeCounters,
} from '../services/api'
import type {
  ScenarioInfo,
  SimulationRunResponse,
  OptimizerResponse,
} from '../types/api'

export function SimulationLabPage() {
  const { lang, t } = useLanguage()

  // State
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [selectedScenarioKey, setSelectedScenarioKey] = useState<string>('scenario_a')
  const [loadingScenarios, setLoadingScenarios] = useState<boolean>(true)

  // Simulation Parameters
  const [durationMinutes, setDurationMinutes] = useState<number>(30)
  const [arrivalRate, setArrivalRate] = useState<number>(1.5)
  const [countersCount, setCountersCount] = useState<number>(3)
  const [priorityRatio, setPriorityRatio] = useState<number>(0.10)
  const [noShowRate, setNoShowRate] = useState<number>(0.05)
  const [durationMultiplier, setDurationMultiplier] = useState<number>(1.0)
  const [randomSeed, setRandomSeed] = useState<number>(42)

  // Execution state
  const [isSimulating, setIsSimulating] = useState<boolean>(false)
  const [simulationResult, setSimulationResult] = useState<SimulationRunResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'kpis' | 'accuracy' | 'optimizer' | 'breakdown'>('kpis')

  // Optimizer state
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false)
  const [optimizerResult, setOptimizerResult] = useState<OptimizerResponse | null>(null)

  // Error & notification state
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Load scenarios on mount
  useEffect(() => {
    async function fetchScenarios() {
      try {
        setLoadingScenarios(true)
        const data = await getScenarios()
        setScenarios(data)
        if (data.length > 0) {
          applyScenarioDefaults(data[0])
        }
      } catch (err) {
        console.error('Failed to load scenarios', err)
        setErrorMsg('Failed to load preset scenarios from backend.')
      } finally {
        setLoadingScenarios(false)
      }
    }
    fetchScenarios()
  }, [])

  function applyScenarioDefaults(scenario: ScenarioInfo) {
    setSelectedScenarioKey(scenario.key)
    setDurationMinutes(Math.round(scenario.duration_seconds / 60))
    setArrivalRate(scenario.arrival_rate_per_minute)
    setCountersCount(scenario.active_counters_count)
    setPriorityRatio(scenario.priority_ratio)
    setNoShowRate(scenario.no_show_rate)
    setDurationMultiplier(scenario.service_duration_multiplier)
  }

  function handleSelectScenario(scenario: ScenarioInfo) {
    applyScenarioDefaults(scenario)
  }

  // Run simulation
  async function handleRunSimulation(customOverrides?: Record<string, unknown>) {
    try {
      setIsSimulating(true)
      setErrorMsg(null)

      const payload = {
        scenario_key: selectedScenarioKey,
        random_seed: randomSeed,
        duration_seconds: durationMinutes * 60,
        arrival_rate_per_minute: arrivalRate,
        active_counters_count: countersCount,
        priority_ratio: priorityRatio,
        no_show_rate: noShowRate,
        service_duration_multiplier: durationMultiplier,
        target_sla_seconds: 600,
        ...customOverrides,
      }

      const res = await runSimulation(payload, true)
      setSimulationResult(res)

      // Also trigger initial optimization calculation for comparison
      triggerOptimizer()
    } catch (err: unknown) {
      console.error('Simulation execution failed', err)
      const message = err instanceof Error ? err.message : 'Simulation failed to run.'
      setErrorMsg(message)
    } finally {
      setIsSimulating(false)
    }
  }

  // Calculate optimization
  async function triggerOptimizer() {
    try {
      setIsOptimizing(true)
      const targetServices = [
        {
          code: 'GEN',
          name: 'General Inquiries',
          arrival_rate_per_min: arrivalRate * 0.45,
          avg_duration_seconds: 180 * durationMultiplier,
          current_counters: Math.max(1, Math.floor(countersCount / 2)),
        },
        {
          code: 'DOC',
          name: 'Document Verification',
          arrival_rate_per_min: arrivalRate * 0.35,
          avg_duration_seconds: 240 * durationMultiplier,
          current_counters: 1,
        },
        {
          code: 'CASH',
          name: 'Cashier & Fees',
          arrival_rate_per_min: arrivalRate * 0.20,
          avg_duration_seconds: 150 * durationMultiplier,
          current_counters: Math.max(1, countersCount - Math.floor(countersCount / 2) - 1),
        },
      ]

      const opt = await optimizeCounters({
        total_counters: countersCount,
        target_sla_seconds: 600,
        services: targetServices,
      })
      setOptimizerResult(opt)
    } catch (err) {
      console.error('Optimizer calculation failed', err)
    } finally {
      setIsOptimizing(false)
    }
  }

  // One-click Re-simulate with optimized allocation
  async function handleApplyOptimizedCounters() {
    if (!optimizerResult) return
    setActiveTab('kpis')
    // Build custom counter assignments from recommended allocation
    const customCounters: Record<string, string[]> = {}
    let counterIndex = 1
    optimizerResult.services.forEach((s) => {
      for (let i = 0; i < s.recommended_counters; i++) {
        customCounters[`Counter ${counterIndex}`] = [s.service_code]
        counterIndex++
      }
    })

    await handleRunSimulation({
      custom_counter_assignments: customCounters,
      name: `Optimized: ${selectedScenario?.title || 'Scenario'}`,
    })
  }

  const selectedScenario = scenarios.find((s) => s.key === selectedScenarioKey)

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-slate-800/80 to-indigo-950/40 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
              <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              {lang === 'ur' ? 'تجربہ گاہ و خودکار تقسیم' : 'Challenge Scenarios A–F & Counter Optimizer'}
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
              {t.simulationLab}
            </h1>
            <p className="text-sm sm:text-base text-slate-300 max-w-2xl">
              {t.simulationSubtitle}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => handleRunSimulation()}
              disabled={isSimulating}
              id="btn-run-simulation-top"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 active:scale-95 transition-all disabled:opacity-50"
            >
              {isSimulating ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>{t.runningSimulation}</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>{t.runSimulationBtn}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300 flex items-center gap-3">
          <span>⚠️</span>
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Preset Scenarios Selector (A through F) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🔬</span>
            <span>{t.presetScenarios}</span>
          </h2>
          <span className="text-xs text-slate-400">
            {scenarios.length} {lang === 'ur' ? 'منظرنامے دستیاب ہیں' : 'Preset Challenge Scenarios'}
          </span>
        </div>

        {loadingScenarios ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-36 rounded-2xl border border-slate-800 bg-slate-800/40 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="scenarios-grid">
            {scenarios.map((sc) => {
              const isSelected = selectedScenarioKey === sc.key
              const badgeColors: Record<string, string> = {
                emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                rose: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
                purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
                sky: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
                indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
              }

              return (
                <button
                  key={sc.key}
                  onClick={() => handleSelectScenario(sc)}
                  id={`scenario-card-${sc.code.toLowerCase()}`}
                  className={`text-left rounded-2xl border p-5 transition-all relative overflow-hidden group ${
                    isSelected
                      ? 'border-emerald-500/80 bg-gradient-to-br from-slate-800/90 to-emerald-950/30 shadow-xl shadow-emerald-500/10 ring-2 ring-emerald-500/30 scale-[1.01]'
                      : 'border-slate-800/80 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-850'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${badgeColors[sc.badge_color] || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
                      <span className="font-bold">Scenario {sc.code}</span>
                      <span>•</span>
                      <span>{sc.category}</span>
                    </span>

                    {isSelected && (
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-slate-950 shadow">
                        ✓
                      </span>
                    )}
                  </div>

                  <h3 className="font-bold text-white text-base group-hover:text-emerald-300 transition-colors">
                    {lang === 'ur' ? sc.title_ur : sc.title}
                  </h3>

                  <p className="mt-1.5 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {lang === 'ur' ? sc.description_ur : sc.description}
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-3 gap-2 text-[11px] text-slate-300">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Arrivals</span>
                      <span className="font-semibold text-white">{sc.arrival_rate_per_minute}/min</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Counters</span>
                      <span className="font-semibold text-white">{sc.active_counters_count} active</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Priority</span>
                      <span className="font-semibold text-white">{Math.round(sc.priority_ratio * 100)}%</span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Parameter Controls & Configuration Grid */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-xl shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>⚙️</span>
              <span>{t.customParameters}</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {lang === 'ur'
                ? 'کسی بھی پیرامیٹر کو تبدیل کر کے قطار پر اس کے اثرات دیکھیں'
                : 'Fine-tune arrival rates, counter capacities, and priority triage parameters'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setRandomSeed(Math.floor(Math.random() * 9000) + 1000)}
              className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 text-xs text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
            >
              🎲 {lang === 'ur' ? 'نیا سیڈ' : 'Randomize Seed'}
            </button>
            <span className="text-xs text-slate-400 font-mono bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
              seed: {randomSeed}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Duration */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.simulationDuration}</label>
              <span className="text-emerald-400 font-semibold">{durationMinutes} min</span>
            </div>
            <input
              type="range"
              min={10}
              max={120}
              step={5}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* Arrival Rate */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.arrivalRateLabel}</label>
              <span className="text-emerald-400 font-semibold">{arrivalRate.toFixed(1)}/min</span>
            </div>
            <input
              type="range"
              min={0.5}
              max={8.0}
              step={0.1}
              value={arrivalRate}
              onChange={(e) => setArrivalRate(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* Active Counters */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.activeCountersLabel}</label>
              <span className="text-emerald-400 font-semibold">{countersCount} Desks</span>
            </div>
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={countersCount}
              onChange={(e) => setCountersCount(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* Priority Influx */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.priorityRatioLabel}</label>
              <span className="text-emerald-400 font-semibold">{Math.round(priorityRatio * 100)}%</span>
            </div>
            <input
              type="range"
              min={0.0}
              max={0.60}
              step={0.05}
              value={priorityRatio}
              onChange={(e) => setPriorityRatio(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* No Show Rate */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.noShowRateLabel}</label>
              <span className="text-emerald-400 font-semibold">{Math.round(noShowRate * 100)}%</span>
            </div>
            <input
              type="range"
              min={0.0}
              max={0.50}
              step={0.05}
              value={noShowRate}
              onChange={(e) => setNoShowRate(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* Duration Multiplier */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <label className="text-slate-300 font-medium">{t.serviceDurationMultLabel}</label>
              <span className="text-emerald-400 font-semibold">{durationMultiplier.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min={0.5}
              max={3.0}
              step={0.1}
              value={durationMultiplier}
              onChange={(e) => setDurationMultiplier(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* Execute Action */}
          <div className="md:col-span-2 flex items-end">
            <button
              onClick={() => handleRunSimulation()}
              disabled={isSimulating}
              id="btn-run-simulation-main"
              className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-3 font-semibold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSimulating ? (
                <>
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>{t.runningSimulation}</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>{t.runSimulationBtn}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Simulation Results Section */}
      {simulationResult && (
        <div className="space-y-6" id="simulation-results-section">
          {/* Navigation Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('kpis')}
                id="tab-kpis"
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === 'kpis'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                📊 KPI Scorecards
              </button>

              <button
                onClick={() => setActiveTab('accuracy')}
                id="tab-accuracy"
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === 'accuracy'
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                🎯 {t.estimateVsActualTitle}
              </button>

              <button
                onClick={() => setActiveTab('optimizer')}
                id="tab-optimizer"
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === 'optimizer'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                ⚡ {t.recommendedAllocation}
              </button>

              <button
                onClick={() => setActiveTab('breakdown')}
                id="tab-breakdown"
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === 'breakdown'
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                🏢 Desks & Services Breakdown
              </button>
            </div>

            <div className="text-xs text-slate-400 font-mono">
              Total Tokens: <span className="text-white font-bold">{simulationResult.total_tokens_issued}</span> | Completed: <span className="text-emerald-400 font-bold">{simulationResult.completed_tokens}</span>
            </div>
          </div>

          {/* TAB 1: KPI SCORECARDS */}
          {activeTab === 'kpis' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {/* Average Wait */}
                <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
                  <div className="text-xs font-medium text-slate-400">{t.estimatedWait} (Avg)</div>
                  <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-white">
                    {Math.floor(simulationResult.kpi_metrics.avg_wait_seconds / 60)}m {simulationResult.kpi_metrics.avg_wait_seconds % 60}s
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    Median: {Math.round(simulationResult.kpi_metrics.median_wait_seconds / 60)}m
                  </div>
                </div>

                {/* 95th Percentile Wait */}
                <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
                  <div className="text-xs font-medium text-slate-400">P95 / Max Wait</div>
                  <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-amber-400">
                    {Math.round(simulationResult.kpi_metrics.p95_wait_seconds / 60)}m
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    Peak: {Math.round(simulationResult.kpi_metrics.max_wait_seconds / 60)}m
                  </div>
                </div>

                {/* Counter Utilization */}
                <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
                  <div className="text-xs font-medium text-slate-400">{t.counterUtilization}</div>
                  <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-emerald-400">
                    {simulationResult.kpi_metrics.counter_utilization_pct}%
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    {simulationResult.counters.length} active counters
                  </div>
                </div>

                {/* SLA Compliance */}
                <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
                  <div className="text-xs font-medium text-slate-400">{t.slaCompliance}</div>
                  <div className={`mt-2 text-2xl sm:text-3xl font-extrabold ${simulationResult.kpi_metrics.sla_breach_pct > 20 ? 'text-rose-400' : 'text-teal-400'}`}>
                    {(100 - simulationResult.kpi_metrics.sla_breach_pct).toFixed(1)}%
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    {simulationResult.kpi_metrics.sla_breach_count} breaches
                  </div>
                </div>

                {/* Throughput */}
                <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg col-span-2 sm:col-span-1">
                  <div className="text-xs font-medium text-slate-400">{t.tokenThroughput}</div>
                  <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-indigo-400">
                    {simulationResult.kpi_metrics.throughput_per_hour}/hr
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    {simulationResult.unserved_waiting_tokens} unserved at cutoff
                  </div>
                </div>
              </div>

              {/* Priority Triage Comparison Card */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
                <div>
                  <h3 className="font-bold text-white text-base flex items-center gap-2">
                    <span>🎖️</span>
                    <span>Priority Triage Impact (Senior / Emergency vs Regular)</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-xl">
                    Demonstrates how priority tokens bypass standard FIFO wait times while regular citizens experience slight queuing deferrals.
                  </p>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <span className="text-[11px] text-indigo-300 block font-medium">Priority Citizen Wait</span>
                    <span className="text-2xl font-extrabold text-indigo-400">
                      {Math.floor(simulationResult.kpi_metrics.avg_priority_wait_seconds / 60)}m {simulationResult.kpi_metrics.avg_priority_wait_seconds % 60}s
                    </span>
                  </div>

                  <span className="text-slate-600 text-2xl font-light">vs</span>

                  <div className="text-center">
                    <span className="text-[11px] text-slate-400 block font-medium">Standard Citizen Wait</span>
                    <span className="text-2xl font-extrabold text-slate-200">
                      {Math.floor(simulationResult.kpi_metrics.avg_standard_wait_seconds / 60)}m {simulationResult.kpi_metrics.avg_standard_wait_seconds % 60}s
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: ESTIMATE VS ACTUAL FIDELITY (EXIT CONDITION) */}
          {activeTab === 'accuracy' && (
            <div className="space-y-6">
              {/* Accuracy Hero Metric */}
              <div className="rounded-3xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 p-6 sm:p-8 backdrop-blur-xl flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
                    <span>🎯</span>
                    <span>Wait Estimator Fidelity Benchmark</span>
                  </div>
                  <h3 className="text-2xl font-extrabold text-white">
                    {simulationResult.estimate_vs_actual.overall_accuracy_pct}% Accuracy Score
                  </h3>
                  <p className="text-sm text-slate-300 max-w-xl">
                    Comparing estimated wait predictions assigned at arrival against actual service call timestamps. Mean Absolute Error: <span className="font-bold text-indigo-300">{simulationResult.estimate_vs_actual.mean_absolute_error_seconds} seconds</span>.
                  </p>
                </div>

                <div className="flex items-center gap-4 bg-slate-950/60 p-5 rounded-2xl border border-indigo-500/20">
                  <div className="text-center px-3">
                    <span className="text-xs text-slate-400 block">MAE Deviation</span>
                    <span className="text-2xl font-extrabold text-indigo-400">
                      ±{simulationResult.estimate_vs_actual.mean_absolute_error_seconds}s
                    </span>
                  </div>
                  <div className="h-10 w-px bg-slate-800" />
                  <div className="text-center px-3">
                    <span className="text-xs text-slate-400 block">Samples Analyzed</span>
                    <span className="text-2xl font-extrabold text-emerald-400">
                      {simulationResult.estimate_vs_actual.sample_points.length}
                    </span>
                  </div>
                </div>
              </div>

              {/* Sample Points Comparison Table */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-xl">
                <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                  <h4 className="font-bold text-white text-sm">
                    Estimate vs Actual Comparison Sample
                  </h4>
                  <span className="text-xs text-slate-400">
                    Evaluating dynamic estimate precision
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="py-3 px-4">Token #</th>
                        <th className="py-3 px-4">Service</th>
                        <th className="py-3 px-4">Priority</th>
                        <th className="py-3 px-4">Predicted Wait</th>
                        <th className="py-3 px-4">Actual Wait</th>
                        <th className="py-3 px-4">Deviation</th>
                        <th className="py-3 px-4 text-right">Fidelity %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {simulationResult.estimate_vs_actual.sample_points.map((pt, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-4 font-bold text-white">{pt.token_number}</td>
                          <td className="py-3 px-4 text-slate-300">{pt.service_code}</td>
                          <td className="py-3 px-4">
                            {pt.priority === 1 ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 font-sans font-semibold">Priority</span>
                            ) : (
                              <span className="text-slate-400 font-sans">Standard</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-indigo-300 font-semibold">{Math.round(pt.estimated_wait_seconds / 60)}m {pt.estimated_wait_seconds % 60}s</td>
                          <td className="py-3 px-4 text-emerald-300 font-semibold">{Math.round(pt.actual_wait_seconds / 60)}m {pt.actual_wait_seconds % 60}s</td>
                          <td className="py-3 px-4 text-slate-400">
                            {pt.error_seconds > 0 ? `+${pt.error_seconds}s` : `${pt.error_seconds}s`}
                          </td>
                          <td className="py-3 px-4 text-right font-bold text-teal-400">
                            {pt.accuracy_pct}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: COUNTER ALLOCATION OPTIMIZER */}
          {activeTab === 'optimizer' && (
            <div className="space-y-6">
              {optimizerResult ? (
                <>
                  {/* Optimizer Impact Hero Card */}
                  <div className="rounded-3xl border border-amber-500/30 bg-gradient-to-br from-amber-950/30 via-slate-900 to-slate-900 p-6 sm:p-8 backdrop-blur-xl shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="space-y-2">
                      <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
                        <span>⚡</span>
                        <span>M/M/c Algorithmic Allocation Engine</span>
                      </div>
                      <h3 className="text-3xl font-extrabold text-white">
                        {optimizerResult.wait_reduction_pct > 0 ? `-${optimizerResult.wait_reduction_pct}% Wait Time Reduction` : 'Balanced Optimal Allocation'}
                      </h3>
                      <p className="text-sm text-slate-300 max-w-xl">
                        Based on queue arrival rates and service durations, reallocating counters eliminates bottleneck queues and balances staff workload.
                      </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center gap-4">
                      <div className="bg-slate-950/80 px-6 py-4 rounded-2xl border border-amber-500/20 text-center">
                        <span className="text-xs text-slate-400 block">Current Wait</span>
                        <span className="text-xl font-bold text-slate-300">{Math.round(optimizerResult.current_avg_wait_seconds / 60)} min</span>
                        <span className="text-[10px] text-slate-400 block mt-1">SLA: {optimizerResult.current_sla_compliance_pct}%</span>
                      </div>

                      <div className="text-amber-400 text-2xl font-bold">➔</div>

                      <div className="bg-slate-950/80 px-6 py-4 rounded-2xl border border-emerald-500/30 text-center">
                        <span className="text-xs text-emerald-400 block font-semibold">Optimized Wait</span>
                        <span className="text-xl font-extrabold text-emerald-400">{Math.round(optimizerResult.recommended_avg_wait_seconds / 60)} min</span>
                        <span className="text-[10px] text-emerald-300 block mt-1">SLA: {optimizerResult.recommended_sla_compliance_pct}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Per-Service Allocation Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {optimizerResult.services.map((s) => {
                      const diff = s.recommended_counters - s.current_counters
                      return (
                        <div key={s.service_code} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white text-base">{s.service_name}</span>
                            <span className="text-xs font-mono text-slate-400 font-semibold">{s.service_code}</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800">
                            <div>
                              <span className="text-slate-400 block">Current Desks</span>
                              <span className="text-base font-bold text-slate-300">{s.current_counters}</span>
                            </div>
                            <div>
                              <span className="text-emerald-400 block font-medium">Recommended</span>
                              <span className="text-base font-extrabold text-emerald-400">
                                {s.recommended_counters} {diff > 0 ? `(+${diff})` : diff < 0 ? `(${diff})` : ''}
                              </span>
                            </div>
                          </div>

                          <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/60 flex items-center justify-between">
                            <span>Utilization: {s.current_utilization_pct}% ➔ {s.recommended_utilization_pct}%</span>
                            <span className="text-emerald-400 font-semibold">-{s.wait_reduction_seconds}s</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Actionable Recommendations List */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
                    <h4 className="font-bold text-white text-sm flex items-center gap-2">
                      <span>📋</span>
                      <span>Actionable Staff Allocation Guidance</span>
                    </h4>

                    <div className="space-y-2">
                      {optimizerResult.actionable_recommendations.map((rec, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-slate-850 border border-slate-800 text-xs text-slate-200">
                          <span className="text-amber-400 font-bold">•</span>
                          <div className="space-y-1">
                            <div>{rec}</div>
                            {optimizerResult.actionable_recommendations_ur[idx] && (
                              <div className="text-slate-400 text-[11px] font-sans" dir="rtl">
                                {optimizerResult.actionable_recommendations_ur[idx]}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Apply Button */}
                    <div className="pt-2">
                      <button
                        onClick={handleApplyOptimizedCounters}
                        disabled={isSimulating}
                        id="btn-re-simulate-optimized"
                        className="rounded-xl bg-gradient-to-r from-amber-500 to-emerald-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-500/20 hover:from-amber-400 hover:to-emerald-500 active:scale-95 transition-all flex items-center gap-2"
                      >
                        <span>🔄</span>
                        <span>{t.reSimulateOptimized}</span>
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  {isOptimizing ? 'Calculating optimal counter allocation...' : 'Run a simulation to generate counter recommendations.'}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: DETAILED BREAKDOWN */}
          {activeTab === 'breakdown' && (
            <div className="space-y-6">
              {/* Counters performance */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
                <h4 className="font-bold text-white text-sm">Physical Counters Utilization</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {simulationResult.counters.map((c) => (
                    <div key={c.counter_name} className="p-4 rounded-xl border border-slate-800 bg-slate-850 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{c.counter_name}</span>
                        <span className="text-xs font-bold text-emerald-400">{c.utilization_pct}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full transition-all"
                          style={{ width: `${Math.min(100, c.utilization_pct)}%` }}
                        />
                      </div>
                      <div className="text-[11px] text-slate-400 flex justify-between">
                        <span>Tokens Served: {c.tokens_served}</span>
                        <span>Busy: {Math.round(c.busy_time_seconds / 60)}m</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Service categories breakdown */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
                <h4 className="font-bold text-white text-sm">Service Categories Performance</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(simulationResult.service_breakdown).map(([code, data]) => (
                    <div key={code} className="p-4 rounded-xl border border-slate-800 bg-slate-850 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{data.name}</span>
                        <span className="text-xs font-mono text-indigo-400 font-semibold">{code}</span>
                      </div>
                      <div className="text-xs text-slate-300 space-y-1 pt-2 border-t border-slate-800">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Total Issued:</span>
                          <span className="font-semibold text-white">{data.total_issued}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Completed:</span>
                          <span className="font-semibold text-emerald-400">{data.completed}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Average Wait:</span>
                          <span className="font-semibold text-white">{Math.round(data.avg_wait_seconds / 60)} min</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Peak Wait:</span>
                          <span className="font-semibold text-amber-400">{Math.round(data.max_wait_seconds / 60)} min</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

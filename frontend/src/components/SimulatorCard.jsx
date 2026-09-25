import React from 'react';
import { Sliders, Play, RotateCcw, ShieldAlert, Sparkles, TrendingUp, Zap, CheckCircle2 } from 'lucide-react';

export default function SimulatorCard({
  baseMultiplier,
  setBaseMultiplier,
  dailyMoveLimit,
  setDailyMoveLimit,
  onRunSimulation,
  simulationResults,
  isSimulating = false,
  onResetSimulation,
}) {
  const revenueDelta = typeof simulationResults?.revenue_delta_pct === 'number' ? simulationResults.revenue_delta_pct : 0.0;
  const bookingRateDelta = typeof simulationResults?.booking_rate_delta_pct === 'number' ? simulationResults.booking_rate_delta_pct : 0.0;
  const breaches = typeof simulationResults?.breaches === 'number' ? simulationResults.breaches : 0;

  const applyPreset = (mult, move) => {
    setBaseMultiplier(mult);
    setDailyMoveLimit(move);
    if (onRunSimulation) {
      onRunSimulation(mult, move);
    }
  };

  return (
    <div className="glass-panel p-5 flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                Safe What-If Strategy Simulator
              </h3>
              <p className="text-xs text-slate-400">
                Test custom pricing sensitivity without affecting live inventory
              </p>
            </div>
          </div>
          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-mono font-semibold">
            Sandbox Active
          </span>
        </div>

        {/* Quick Strategy Presets */}
        <div className="mb-4">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Quick Strategy Presets (Click to Simulate)
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => applyPreset(1.25, 0.25)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 text-left text-xs transition hover:border-amber-500/40 active:scale-95"
            >
              <div className="font-semibold text-amber-300 flex items-center">
                <Zap className="w-3 h-3 mr-1" />
                Festival Surge
              </div>
              <span className="text-[10px] text-slate-400 font-mono">1.25x &bull; ±25%</span>
            </button>

            <button
              type="button"
              onClick={() => applyPreset(1.00, 0.15)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 text-left text-xs transition hover:border-teal-500/40 active:scale-95"
            >
              <div className="font-semibold text-teal-300 flex items-center">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                Balanced
              </div>
              <span className="text-[10px] text-slate-400 font-mono">1.00x &bull; ±15%</span>
            </button>

            <button
              type="button"
              onClick={() => applyPreset(0.90, 0.10)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 text-left text-xs transition hover:border-blue-500/40 active:scale-95"
            >
              <div className="font-semibold text-blue-300 flex items-center">
                <Sparkles className="w-3 h-3 mr-1" />
                Conservative
              </div>
              <span className="text-[10px] text-slate-400 font-mono">0.90x &bull; ±10%</span>
            </button>
          </div>
        </div>

        {/* Sliders Area */}
        <div className="space-y-4 mb-5">
          {/* 1. Base Multiplier Slider */}
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs mb-2">
              <span className="text-slate-300 font-medium">Base Multiplier Scalar:</span>
              <span className="font-mono font-bold text-teal-300 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                {parseFloat(baseMultiplier).toFixed(2)}x ({baseMultiplier >= 1 ? `+${Math.round((baseMultiplier - 1) * 100)}%` : `-${Math.round((1 - baseMultiplier) * 100)}%`})
              </span>
            </div>
            <input
              type="range"
              min="0.50"
              max="2.00"
              step="0.05"
              value={baseMultiplier}
              onChange={(e) => setBaseMultiplier(parseFloat(e.target.value))}
              onMouseUp={() => onRunSimulation && onRunSimulation(baseMultiplier, dailyMoveLimit)}
              onTouchEnd={() => onRunSimulation && onRunSimulation(baseMultiplier, dailyMoveLimit)}
              className="w-full accent-teal-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>0.50x (Deep Discount)</span>
              <span>1.00x (Baseline)</span>
              <span>2.00x (Aggressive Peak)</span>
            </div>
          </div>

          {/* 2. Daily Move Limit Slider */}
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs mb-2">
              <span className="text-slate-300 font-medium">Daily Movement Volatility Cap:</span>
              <span className="font-mono font-bold text-amber-300 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                ±{(parseFloat(dailyMoveLimit) * 100).toFixed(0)}% per day
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.01"
              value={dailyMoveLimit}
              onChange={(e) => setDailyMoveLimit(parseFloat(e.target.value))}
              onMouseUp={() => onRunSimulation && onRunSimulation(baseMultiplier, dailyMoveLimit)}
              onTouchEnd={() => onRunSimulation && onRunSimulation(baseMultiplier, dailyMoveLimit)}
              className="w-full accent-amber-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>±5% (Strict Stability)</span>
              <span>±20% (Default)</span>
              <span>±50% (High Volatility)</span>
            </div>
          </div>
        </div>

        {/* Projected Impact Cards */}
        <div className="mb-5">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Projected 30-Day Financial Impact
          </div>
          <div className="grid grid-cols-3 gap-2">
            {/* Revenue Delta */}
            <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Revenue Delta</div>
              <div className={`text-lg font-black font-mono mt-1 ${revenueDelta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {revenueDelta >= 0 ? `+${revenueDelta}%` : `${revenueDelta}%`}
              </div>
            </div>

            {/* Booking Rate Delta */}
            <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Conversion Delta</div>
              <div className={`text-lg font-black font-mono mt-1 ${bookingRateDelta >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {bookingRateDelta >= 0 ? `+${bookingRateDelta}%` : `${bookingRateDelta}%`}
              </div>
            </div>

            {/* Guardrail Clamped Count */}
            <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Clamped Dates</div>
              <div className={`text-lg font-black font-mono mt-1 ${breaches === 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {breaches} dates
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Buttons */}
      <div className="space-y-2 pt-3 border-t border-slate-800">
        <button
          onClick={onRunSimulation}
          disabled={isSimulating}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 active:scale-[0.99] text-white font-bold text-xs transition shadow-lg shadow-teal-500/20 flex items-center justify-center space-x-2 disabled:opacity-50"
        >
          {isSimulating ? (
            <span className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Running Simulation Algorithm...</span>
            </span>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Simulate Scenario (Call /pricing/simulate)</span>
            </>
          )}
        </button>

        <button
          onClick={onResetSimulation}
          className="w-full py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition flex items-center justify-center space-x-1.5"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset to Default Strategy</span>
        </button>
      </div>
    </div>
  );
}

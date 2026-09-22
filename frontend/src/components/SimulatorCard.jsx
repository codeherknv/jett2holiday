import React, { useState } from 'react';
import { Sliders, Play, RotateCcw, AlertTriangle, ShieldAlert, Sparkles, TrendingUp, Users } from 'lucide-react';

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
  const [manualOverrideActive, setManualOverrideActive] = useState(false);

  const revenueDelta = simulationResults?.revenue_delta_pct ?? 12.4;
  const bookingRateDelta = simulationResults?.booking_rate_delta_pct ?? -2.1;
  const breaches = simulationResults?.breaches ?? 0;

  return (
    <div className="glass-panel p-5 flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Safe Simulation &bull; What-If Scenario
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Test rate shifts before they reach live inventory
            </p>
          </div>
          <span className="text-xs px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800 font-mono">
            Sandbox
          </span>
        </div>

        {/* Sliders Area */}
        <div className="space-y-4 mb-5">
          {/* 1. Base Multiplier Slider */}
          <div>
            <div className="flex justify-between items-center text-xs mb-1.5">
              <span className="text-slate-300 font-medium">Base Multiplier:</span>
              <span className="font-mono font-bold text-teal-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                {parseFloat(baseMultiplier).toFixed(2)}x
              </span>
            </div>
            <input
              type="range"
              min="0.50"
              max="2.00"
              step="0.05"
              value={baseMultiplier}
              onChange={(e) => setBaseMultiplier(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>0.50x (Discount)</span>
              <span>1.00x (Neutral)</span>
              <span>2.00x (Aggressive)</span>
            </div>
          </div>

          {/* 2. Daily Move Limit Slider */}
          <div>
            <div className="flex justify-between items-center text-xs mb-1.5">
              <span className="text-slate-300 font-medium">Daily Move Limit:</span>
              <span className="font-mono font-bold text-amber-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                {(parseFloat(dailyMoveLimit) * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.01"
              value={dailyMoveLimit}
              onChange={(e) => setDailyMoveLimit(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>5% (Strict clamp)</span>
              <span>20% (Default)</span>
              <span>50% (Volatile)</span>
            </div>
          </div>
        </div>

        {/* Projected Simulated Impact KPIs */}
        <div className="mb-5">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Simulated Impact Projections
          </div>
          <div className="grid grid-cols-3 gap-2">
            {/* Revenue Delta */}
            <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded-lg text-center">
              <div className="text-[10px] text-slate-400 uppercase">Revenue</div>
              <div className={`text-sm font-bold font-mono mt-0.5 ${revenueDelta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {revenueDelta >= 0 ? `+${revenueDelta}%` : `${revenueDelta}%`}
              </div>
            </div>

            {/* Booking Rate Delta */}
            <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded-lg text-center">
              <div className="text-[10px] text-slate-400 uppercase">Booking Rate</div>
              <div className={`text-sm font-bold font-mono mt-0.5 ${bookingRateDelta >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {bookingRateDelta >= 0 ? `+${bookingRateDelta}%` : `${bookingRateDelta}%`}
              </div>
            </div>

            {/* Guardrail Breaches */}
            <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded-lg text-center">
              <div className="text-[10px] text-slate-400 uppercase">Breaches</div>
              <div className={`text-sm font-bold font-mono mt-0.5 ${breaches === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {breaches} dates
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2 pt-3 border-t border-slate-800">
        <button
          onClick={onRunSimulation}
          disabled={isSimulating}
          className="w-full py-2 px-4 rounded-lg bg-teal-600 hover:bg-teal-500 active:bg-teal-700 text-white font-semibold text-xs transition-all shadow-lg shadow-teal-600/20 flex items-center justify-center space-x-2 disabled:opacity-50"
        >
          {isSimulating ? (
            <span className="flex items-center space-x-2">
              <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Running Simulation...</span>
            </span>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Apply Simulation (Call /pricing/simulate)</span>
            </>
          )}
        </button>

        <div className="flex space-x-2">
          <button
            onClick={onResetSimulation}
            className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors flex items-center justify-center space-x-1"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
          <button
            onClick={() => setManualOverrideActive(!manualOverrideActive)}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border transition-colors flex items-center justify-center space-x-1 ${
              manualOverrideActive
                ? 'bg-amber-950 border-amber-700 text-amber-300'
                : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
            }`}
          >
            <ShieldAlert className="w-3 h-3 text-amber-400" />
            <span>{manualOverrideActive ? 'Override Active' : 'Manual Override'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

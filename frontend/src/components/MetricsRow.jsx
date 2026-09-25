import React from 'react';
import { ShieldCheck, TrendingUp, Lock, Gauge, ArrowUpRight, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function MetricsRow({
  floorPrice = 2485.41,
  ceilingPrice = 6130.68,
  maxDailyMovePct = 0.15,
  effectivePrice = 5051.69,
  basePrice = 3697.89,
  boundClamped = false,
}) {
  const priceDeltaPct = basePrice > 0 ? (((effectivePrice - basePrice) / basePrice) * 100).toFixed(1) : '0.0';

  // Calculate price position within floor -> ceiling corridor (0% to 100%)
  const corridorRange = ceilingPrice - floorPrice;
  const corridorPos = corridorRange > 0
    ? Math.max(0, Math.min(100, Math.round(((effectivePrice - floorPrice) / corridorRange) * 100)))
    : 50;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Floor Guardrail Card */}
      <div className="glass-panel p-4 flex flex-col justify-between border-t-2 border-t-emerald-500 hover:-translate-y-0.5 transition-transform duration-200">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
          <span className="uppercase tracking-wider">Floor Guardrail</span>
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="my-2">
          <div className="text-2xl font-bold font-mono text-slate-100">
            ₹{floorPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Strict profitability threshold</p>
        </div>
        <div className="text-[11px] text-emerald-400/90 font-medium flex items-center pt-2 border-t border-slate-800/80">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
          <span>Zero margin erosion guarantee</span>
        </div>
      </div>

      {/* 2. Ceiling Rate Cap Card */}
      <div className="glass-panel p-4 flex flex-col justify-between border-t-2 border-t-blue-500 hover:-translate-y-0.5 transition-transform duration-200">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
          <span className="uppercase tracking-wider">Ceiling Rate Cap</span>
          <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Lock className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="my-2">
          <div className="text-2xl font-bold font-mono text-slate-100">
            ₹{ceilingPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Anti-price gouging ceiling</p>
        </div>
        <div className="text-[11px] text-blue-400/90 font-medium flex items-center pt-2 border-t border-slate-800/80">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mr-1.5"></span>
          <span>Protects guest trust &amp; fairness</span>
        </div>
      </div>

      {/* 3. Max Daily Move Limit */}
      <div className="glass-panel p-4 flex flex-col justify-between border-t-2 border-t-amber-500 hover:-translate-y-0.5 transition-transform duration-200">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
          <span className="uppercase tracking-wider">Daily Volatility Cap</span>
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Gauge className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="my-2">
          <div className="text-2xl font-bold font-mono text-slate-100">
            ±{(maxDailyMovePct * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Max day-over-day price delta</p>
        </div>
        <div className="text-[11px] text-amber-400/90 font-medium flex items-center pt-2 border-t border-slate-800/80">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5"></span>
          <span>Dampens sudden demand shocks</span>
        </div>
      </div>

      {/* 4. Effective Dynamic Price (Hero Card) */}
      <div className="glass-panel p-4 flex flex-col justify-between border-t-2 border-t-teal-400 bg-gradient-to-br from-slate-900 via-slate-900 to-teal-950/40 hover:-translate-y-0.5 transition-transform duration-200">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
          <span className="uppercase tracking-wider text-teal-300">Published Dynamic Rate</span>
          <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <TrendingUp className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="my-2">
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold font-mono text-teal-300">
              ₹{effectivePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`text-[11px] px-2 py-0.5 rounded-full font-mono font-bold ${parseFloat(priceDeltaPct) >= 0
                ? 'bg-teal-950 text-teal-300 border border-teal-800'
                : 'bg-rose-950 text-rose-300 border border-rose-800'
              }`}>
              {parseFloat(priceDeltaPct) >= 0 ? `+${priceDeltaPct}%` : `${priceDeltaPct}%`}
            </span>
          </div>

          {/* Corridor Progress Bar */}
          <div className="mt-2">
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mb-1">
              <span>Corridor: {corridorPos}%</span>
              <span>Baseline: ₹{Math.round(basePrice).toLocaleString('en-IN')}</span>
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden flex">
              <div
                className="bg-gradient-to-r from-emerald-500 via-teal-400 to-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${corridorPos}%` }}
              />
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-300 font-medium flex items-center justify-between pt-2 border-t border-slate-800/80">
          <span className="text-slate-400">Status:</span>
          <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${boundClamped
              ? 'bg-amber-950 text-amber-300 border border-amber-800'
              : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
            }`}>
            {boundClamped ? (
              <>
                <ShieldAlert className="w-3 h-3 mr-1 text-amber-400" />
                <span>CLAMPED BY GUARDRAIL</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-400" />
                <span>WITHIN SAFE BOUNDS</span>
              </>
            )}
          </span>
        </div>
      </div>
    </div>
  );
}

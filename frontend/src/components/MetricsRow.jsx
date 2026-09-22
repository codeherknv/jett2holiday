import React from 'react';
import { ShieldCheck, TrendingUp, ArrowUpRight, Lock, Gauge } from 'lucide-react';

export default function MetricsRow({
  floorPrice = 3500,
  ceilingPrice = 7000,
  maxDailyMovePct = 0.15,
  effectivePrice = 5850,
  basePrice = 4500,
  boundClamped = false,
}) {
  const priceDeltaPct = basePrice > 0 ? (((effectivePrice - basePrice) / basePrice) * 100).toFixed(1) : '0.0';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Floor Guardrail */}
      <div className="glass-panel p-4 flex flex-col justify-between border-l-4 border-l-emerald-500">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
          <span className="uppercase tracking-wider">Floor Guardrail</span>
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-100">
          ₹{floorPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
          <span className="text-emerald-400 font-semibold">Strict Minimum</span>
          <span>• Base hard floor</span>
        </div>
      </div>

      {/* 2. Ceiling Cap */}
      <div className="glass-panel p-4 flex flex-col justify-between border-l-4 border-l-blue-500">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
          <span className="uppercase tracking-wider">Ceiling Cap</span>
          <Lock className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-100">
          ₹{ceilingPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
          <span className="text-blue-400 font-semibold">Max Rate Cap</span>
          <span>• Prevents gouging</span>
        </div>
      </div>

      {/* 3. Max Daily Move Limit */}
      <div className="glass-panel p-4 flex flex-col justify-between border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
          <span className="uppercase tracking-wider">Max Daily Move</span>
          <Gauge className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-100">
          {(maxDailyMovePct * 100).toFixed(1)}%
        </div>
        <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
          <span className="text-amber-400 font-semibold">Protected</span>
          <span>• Intra-day volatility clamp</span>
        </div>
      </div>

      {/* 4. Effective Dynamic Price */}
      <div className="glass-panel p-4 flex flex-col justify-between border-l-4 border-l-teal-500 bg-gradient-to-br from-slate-900 via-slate-900 to-teal-950/30">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
          <span className="uppercase tracking-wider text-teal-300">Effective Dynamic Price</span>
          <TrendingUp className="w-4 h-4 text-teal-400" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-extrabold font-mono text-teal-300">
            ₹{effectivePrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
            parseFloat(priceDeltaPct) >= 0 ? 'bg-teal-950 text-teal-400 border border-teal-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
          }`}>
            {parseFloat(priceDeltaPct) >= 0 ? `+${priceDeltaPct}%` : `${priceDeltaPct}%`}
          </span>
        </div>
        <div className="text-xs text-slate-400 mt-1 flex items-center justify-between">
          <span>Base benchmark: ₹{basePrice.toLocaleString('en-IN')}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
            boundClamped ? 'bg-amber-900/80 text-amber-300' : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
          }`}>
            {boundClamped ? 'CLAMPED' : 'WITHIN BOUNDS'}
          </span>
        </div>
      </div>
    </div>
  );
}

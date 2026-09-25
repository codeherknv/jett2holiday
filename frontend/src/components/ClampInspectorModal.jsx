import React from 'react';
import { X, ShieldAlert, ShieldCheck, ArrowRight, TrendingUp, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export default function ClampInspectorModal({
  isOpen,
  onClose,
  pointData,
  entityName = 'Selected Entity',
  locale = 'en-IN',
  onOpenOverride
}) {
  if (!isOpen || !pointData) return null;

  const rawPrice = pointData.raw_model_price || (pointData.base_price * (1 + (pointData.demand_index - 1) * 0.7));
  const publishedPrice = pointData.simulated_price || pointData.current_dynamic_price || pointData.price;
  const isClamped = pointData.clamped;
  const clampedBy = pointData.clamped_by || (rawPrice > pointData.ceiling_price ? 'ceiling' : (rawPrice < pointData.floor_price ? 'floor' : 'daily_movement'));
  const boundName = pointData.bound_name || (clampedBy === 'ceiling' ? `Ceiling Cap (₹${pointData.ceiling_price?.toLocaleString('en-IN')})` : (clampedBy === 'floor' ? `Floor Cap (₹${pointData.floor_price?.toLocaleString('en-IN')})` : 'Max Daily Movement'));
  const boundValue = pointData.bound_value || (clampedBy === 'ceiling' ? pointData.ceiling_price : pointData.floor_price);

  const deltaPrice = Math.abs(rawPrice - publishedPrice);
  const deltaPct = rawPrice > 0 ? Math.round((deltaPrice / rawPrice) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl p-6 text-slate-100 overflow-hidden">
        {/* Glow Header */}
        <div className={`absolute top-0 left-0 right-0 h-1.5 ${
          clampedBy === 'ceiling' ? 'bg-amber-500' : (clampedBy === 'floor' ? 'bg-emerald-500' : 'bg-cyan-500')
        }`} />

        {/* Modal Top Bar */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                clampedBy === 'ceiling'
                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                  : clampedBy === 'floor'
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
              }`}>
                {isClamped ? (
                  <>
                    <ShieldAlert className="w-3.5 h-3.5 mr-1 text-amber-400" />
                    Guardrail Clamp Active &bull; {clampedBy?.toUpperCase()}
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                    Within Safe Guardrails
                  </>
                )}
              </span>
              <span className="text-xs text-slate-400 font-mono">Date: {pointData.date}</span>
            </div>
            <h2 className="text-lg font-bold text-slate-100 mt-1">
              Guardrail Decision Inspector
            </h2>
            <p className="text-xs text-slate-400 truncate max-w-md">{entityName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 3 Core Price Cards: Raw Price vs Published Price vs Bound */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-5">
          {/* Card 1: Raw Unclamped Price */}
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold flex items-center justify-between">
              <span>Raw Model Price</span>
              <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <div className="my-2">
              <div className="text-xl font-bold font-mono text-slate-300">
                ₹{Math.round(rawPrice).toLocaleString('en-IN')}
              </div>
              <span className="text-[11px] text-slate-500">Unbounded ML proposal</span>
            </div>
            <div className="text-[10px] text-slate-400 border-t border-slate-800/80 pt-1">
              Demand index: <strong className="text-blue-300 font-mono">{pointData.demand_index}x</strong>
            </div>
          </div>

          {/* Card 2: Clamping Named Bound */}
          <div className={`p-3.5 rounded-xl border flex flex-col justify-between ${
            clampedBy === 'ceiling'
              ? 'bg-amber-950/30 border-amber-800/60 text-amber-200'
              : clampedBy === 'floor'
              ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
              : 'bg-cyan-950/30 border-cyan-800/60 text-cyan-200'
          }`}>
            <div className="text-[11px] uppercase tracking-wider font-semibold flex items-center justify-between">
              <span>Binding Guardrail</span>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="my-2">
              <div className="text-xl font-bold font-mono">
                {boundValue ? `₹${Math.round(boundValue).toLocaleString('en-IN')}` : boundName}
              </div>
              <span className="text-[11px] opacity-80">{boundName}</span>
            </div>
            <div className="text-[10px] opacity-75 border-t border-slate-800/60 pt-1">
              {clampedBy === 'ceiling' ? 'Surge ceiling enforced' : (clampedBy === 'floor' ? 'Minimum margin protected' : 'Volatility dampened')}
            </div>
          </div>

          {/* Card 3: Final Published Dynamic Price */}
          <div className="p-3.5 rounded-xl bg-teal-950/40 border border-teal-800/80 flex flex-col justify-between text-teal-200">
            <div className="text-[11px] uppercase tracking-wider font-semibold flex items-center justify-between">
              <span>Published Price</span>
              <CheckCircle className="w-3.5 h-3.5 text-teal-400" />
            </div>
            <div className="my-2">
              <div className="text-2xl font-bold font-mono text-teal-300">
                ₹{Math.round(publishedPrice).toLocaleString('en-IN')}
              </div>
              <span className="text-[11px] text-teal-400/90">Safe deployable rate</span>
            </div>
            <div className="text-[10px] text-teal-300/80 border-t border-teal-800/60 pt-1">
              {isClamped ? `Capped by ₹${deltaPrice.toLocaleString('en-IN')} (${deltaPct}%)` : 'Accepted without adjustment'}
            </div>
          </div>
        </div>

        {/* Driving Factors Breakdown Table */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 mb-4">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center">
            <Info className="w-3.5 h-3.5 mr-1.5 text-blue-400" />
            Underlying Driving Factor Decomposition
          </h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">ML Forecast Demand Signal:</span>
              <span className="font-mono text-blue-300 font-semibold">{pointData.demand_index}x (+{Math.round((pointData.demand_index - 1) * 40)}% rate push)</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Baseline Benchmark Price:</span>
              <span className="font-mono text-slate-200">₹{pointData.base_price?.toLocaleString('en-IN')}</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Allowed Floor / Ceiling Range:</span>
              <span className="font-mono text-slate-300">₹{pointData.floor_price?.toLocaleString('en-IN')} — ₹{pointData.ceiling_price?.toLocaleString('en-IN')}</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-400">Clamping Guardrail Action:</span>
              <span className={`font-semibold font-mono ${isClamped ? 'text-amber-300' : 'text-emerald-300'}`}>
                {isClamped ? `Clamped to ${boundName}` : 'Accepted (Zero Clamping)'}
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-[11px] text-slate-400 flex items-center">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block mr-1.5 animate-pulse"></span>
            Audit record registered in SQLite <code className="text-slate-300 font-mono ml-1">price_history</code>
          </div>
          <div className="flex items-center space-x-2">
            {onOpenOverride && (
              <button
                onClick={() => {
                  onClose();
                  onOpenOverride(pointData);
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                Manual Override
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition"
            >
              Close Inspector
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { X, ShieldAlert, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react';
import { setPriceOverride } from '../api/client';

export default function ManualOverrideModal({
  isOpen,
  onClose,
  selectedEntity,
  entityName = 'Selected Entity',
  defaultDate = '2026-10-15',
  floorPrice = 3500,
  ceilingPrice = 7000,
  currentPrice = 5850,
  onOverrideApplied,
}) {
  const [date, setDate] = useState(defaultDate);
  const [overridePrice, setOverridePrice] = useState(currentPrice);
  const [reason, setReason] = useState('VIP Corporate Group Booking Rate');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen) return null;

  const numPrice = parseFloat(overridePrice) || 0;
  const isBelowFloor = numPrice < floorPrice;
  const isAboveCeiling = numPrice > ceilingPrice;
  const hasGuardrailWarning = isBelowFloor || isAboveCeiling;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await setPriceOverride(selectedEntity, date, numPrice, reason);
      setSuccessMsg(`Manual override of ₹${numPrice.toLocaleString('en-IN')} applied successfully for ${date}!`);
      if (onOverrideApplied) {
        onOverrideApplied(res);
      }
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      // Fallback local update
      if (onOverrideApplied) {
        onOverrideApplied({
          entity_id: selectedEntity,
          date,
          override_price: numPrice,
          reason,
          violates_guardrails: hasGuardrailWarning,
        });
      }
      setSuccessMsg(`Manual override of ₹${numPrice.toLocaleString('en-IN')} recorded locally.`);
      setTimeout(() => {
        onClose();
      }, 1000);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl p-6 text-slate-100 overflow-hidden">
        {/* Glow Header */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-500 to-indigo-500" />

        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950 text-blue-300 border border-blue-800">
              Admin Control Plane
            </span>
            <h2 className="text-lg font-bold text-slate-100 mt-1">Manual Price Override</h2>
            <p className="text-xs text-slate-400 truncate max-w-sm">{entityName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 my-5">
          {/* Date Selector */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Target Override Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-blue-500 font-mono"
              required
            />
          </div>

          {/* Override Price Input */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Override Published Price (INR)
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                Bounds: ₹{floorPrice.toLocaleString('en-IN')} – ₹{ceilingPrice.toLocaleString('en-IN')}
              </span>
            </div>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-slate-500 font-bold">₹</span>
              <input
                type="number"
                step="50"
                value={overridePrice}
                onChange={(e) => setOverridePrice(e.target.value)}
                className="w-full pl-8 pr-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-base font-bold font-mono focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            {/* Realtime Guardrail Warning */}
            {hasGuardrailWarning && (
              <div className="mt-2 p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/80 text-amber-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                <span>
                  <strong>Guardrail Notice:</strong> This override rate violates active safety bounds (
                  {isAboveCeiling ? `Ceiling: ₹${ceilingPrice}` : `Floor: ₹${floorPrice}`}). Admin audit flag will be logged.
                </span>
              </div>
            )}
          </div>

          {/* Justification / Reason */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Audit Reason / Justification
            </label>
            <textarea
              rows="2"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
              placeholder="e.g., Match local competitor promotion, bulk tour operator rate..."
              required
            />
          </div>

          {successMsg && (
            <div className="p-2.5 rounded-lg bg-teal-950/50 border border-teal-800 text-teal-300 text-xs flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-teal-400" />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-2.5 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-xs flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-blue-500/20"
            >
              <span>{isSubmitting ? 'Saving...' : 'Apply Manual Override'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

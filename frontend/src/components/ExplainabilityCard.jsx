import React, { useState } from 'react';
import { FileText, ShieldCheck, Download, Languages, CheckCircle2 } from 'lucide-react';

export default function ExplainabilityCard({
  explainData,
  selectedDate = '2026-10-15',
  locale = 'en-IN',
}) {
  const [activeTab, setActiveTab] = useState('en'); // 'en' or 'hi'

  const effectivePrice = explainData?.effective_price || 5850.0;
  const basePrice = explainData?.base_price || 4500.0;
  const factors = explainData?.factors || [
    { name: 'Demand Index (forecast)', value: 1.42, contribution: 0.28 },
    { name: 'Occupancy Factor (85% booked)', value: 1.18, contribution: 0.18 },
    { name: 'Lead Time (14 days out)', value: 1.04, contribution: 0.04 },
    { name: 'Seasonality (Autumn Peak)', value: 1.15, contribution: 0.15 },
  ];

  const explanationEn =
    explainData?.explanation_en ||
    `Price elevated by 30% to ₹${effectivePrice.toLocaleString('en-IN')} due to combined autumn seasonal surge and high property occupancy (85%). No clamping applied; recommendation remains within active floor and ceiling guardrails.`;

  const explanationHi =
    explainData?.explanation_hi ||
    `उच्च मांग, 85% ऑक्यूपेंसी और शरद ऋतु पीक सीजन के कारण मूल्य में 30% की वृद्धि की गई है (₹${effectivePrice.toLocaleString('en-IN')})। यह मूल्य सभी निर्धारित सुरक्षा सीमाओं के भीतर है।`;

  const handleExport = () => {
    const jsonStr = JSON.stringify(
      {
        selectedDate,
        basePrice,
        effectivePrice,
        factors,
        explanationEn,
        explanationHi,
        timestamp: new Date().toISOString(),
      },
      null,
      2
    );
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pricing-audit-${selectedDate}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="glass-panel p-5 flex flex-col justify-between h-full">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Decision Audit &bull; Factor Explainability
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Selected forecast date: <span className="text-teal-300 font-mono">{selectedDate}</span>
            </p>
          </div>

          <button
            onClick={handleExport}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-teal-300 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700 transition-colors"
            title="Export Decision Audit JSON"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>
        </div>

        {/* Effective Price Highlight */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/60 mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Effective Dynamic Price</div>
            <div className="text-xl font-bold font-mono text-teal-300">
              ₹{effectivePrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="flex items-center space-x-1 text-xs text-emerald-400 bg-emerald-950/80 border border-emerald-800/80 px-2.5 py-1 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Within guardrails</span>
          </div>
        </div>

        {/* Factor Decomposition Table */}
        <div className="space-y-2 mb-4">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex justify-between">
            <span>Factor Name</span>
            <span>Value &bull; Contribution</span>
          </div>

          {/* Base Benchmark Row */}
          <div className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-slate-800/30 border border-slate-800 font-mono">
            <span className="text-slate-300">Base Price (benchmark)</span>
            <span className="text-slate-300 font-semibold">₹{basePrice.toLocaleString('en-IN')}</span>
          </div>

          {/* Decomposed Multipliers */}
          {factors.map((factor, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between text-xs py-1.5 px-2 rounded hover:bg-slate-800/40 border border-transparent hover:border-slate-800 transition-colors font-mono"
            >
              <span className="text-slate-300">{factor.name}</span>
              <div className="flex items-center space-x-2">
                <span className="text-slate-400">{factor.value.toFixed(3)}</span>
                <span className="text-teal-400 font-medium">
                  {factor.contribution >= 0 ? `+${(factor.contribution * 100).toFixed(0)}%` : `${(factor.contribution * 100).toFixed(0)}%`}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Multilingual Explanation Summary */}
      <div className="mt-4 pt-3 border-t border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300">
            <FileText className="w-3.5 h-3.5 text-teal-400" />
            <span>Audit Explanation Summary</span>
          </div>
          {/* Language Toggle for Audit Text */}
          <div className="flex items-center space-x-1 text-[11px]">
            <button
              onClick={() => setActiveTab('en')}
              className={`px-1.5 py-0.5 rounded ${
                activeTab === 'en' ? 'bg-teal-700 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setActiveTab('hi')}
              className={`px-1.5 py-0.5 rounded ${
                activeTab === 'hi' ? 'bg-teal-700 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              हिन्दी
            </button>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans min-h-[75px]">
          {activeTab === 'en' ? (
            <p>{explanationEn}</p>
          ) : (
            <p className="font-normal">{explanationHi}</p>
          )}
        </div>
      </div>
    </div>
  );
}

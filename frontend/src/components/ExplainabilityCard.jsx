import React, { useState } from 'react';
import { FileText, Download, ShieldAlert, CheckCircle2, ChevronRight, Sparkles, Layers } from 'lucide-react';

export default function ExplainabilityCard({
  explainData,
  selectedDate = '2026-10-15',
  locale = 'en-IN',
}) {
  const [activeTab, setActiveTab] = useState('en');

  const effectivePrice = explainData?.effective_price || 5051.69;
  const basePrice = explainData?.base_price || 3697.89;
  const isClamped = explainData?.bound_clamped || false;

  const factors = explainData?.factors || [
    { name: 'Demand Signal (ML Ridge β=1.75)', value: 1.23, contribution: 0.081, color: 'from-blue-500 to-cyan-400' },
    { name: 'Occupancy Rate (β=0.0217)', value: 1.05, contribution: 0.016, color: 'from-emerald-500 to-teal-400' },
    { name: 'Seasonality Factor (β=0.0099)', value: 1.18, contribution: 0.036, color: 'from-amber-500 to-orange-400' },
    { name: 'Lead Time (14 Days Out)', value: 1.04, contribution: 0.006, color: 'from-purple-500 to-indigo-400' },
  ];

  const explanationEn =
    explainData?.explanation_en ||
    `Price for this property on ${selectedDate} is calculated at ₹${Math.round(effectivePrice).toLocaleString('en-IN')} (+36.6% vs baseline ₹${Math.round(basePrice).toLocaleString('en-IN')}) driven by strong demand index (1.52x), 85% occupancy, and seasonal weighting. ${isClamped ? 'Notice: Price was bounded by guardrails.' : 'Operates safely within active floor and ceiling guardrails.'}`;

  const explanationHi =
    explainData?.explanation_hi ||
    `${selectedDate} के लिए मूल्य आधार दर ₹${Math.round(basePrice).toLocaleString('en-IN')} से +36.6% बदलकर ₹${Math.round(effectivePrice).toLocaleString('en-IN')} निर्धारित किया गया है। यह निर्णय मांग सूचकांक (1.52x), ऑक्यूपेंसी (85%) और मौसमी प्रभाव पर आधारित है। ${isClamped ? 'सूचना: मूल्य को सुरक्षा सीमा पर क्लैंप किया गया।' : 'यह मूल्य निर्धारित सुरक्षा सीमाओं के अंतर्गत सुरक्षित है।'}`;

  const handleExport = () => {
    const jsonStr = JSON.stringify(
      {
        selectedDate,
        basePrice,
        effectivePrice,
        factors,
        boundClamped: isClamped,
        explanationEn,
        explanationHi,
        exportedAt: new Date().toISOString(),
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

  const factorColors = [
    'bg-blue-500',
    'bg-emerald-500',
    'bg-amber-500',
    'bg-purple-500',
  ];

  return (
    <div className="glass-panel p-5 flex flex-col justify-between h-full">
      <div>
        {/* Card Top Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                Decision Audit &bull; Factor Explainability
              </h3>
              <p className="text-xs text-slate-400">
                Target stay date: <span className="text-teal-300 font-mono font-semibold">{selectedDate}</span>
              </p>
            </div>
          </div>

          <button
            onClick={handleExport}
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-teal-300 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
            title="Download JSON Audit Record"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </div>

        {/* Dynamic Rate Highlight Banner */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 mb-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Published Effective Rate</div>
            <div className="text-2xl font-black font-mono text-teal-300 mt-0.5">
              ₹{effectivePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className={`flex items-center space-x-1.5 text-xs px-3 py-1 rounded-full font-bold border ${isClamped
              ? 'bg-amber-950/80 text-amber-300 border-amber-800'
              : 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
            }`}>
            {isClamped ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                <span>Clamped to Guardrail</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Within Safe Bounds</span>
              </>
            )}
          </div>
        </div>

        {/* Visual Factor Decomposition Waterfall */}
        <div className="space-y-3 mb-5">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex justify-between">
            <span>Factor Name</span>
            <span>Value &bull; Price Impact</span>
          </div>

          {/* Benchmark Row */}
          <div className="flex items-center justify-between text-xs py-2 px-3 rounded-lg bg-slate-800/40 border border-slate-800 font-mono">
            <span className="text-slate-300 font-sans font-medium">Base Price (benchmark baseline)</span>
            <span className="text-slate-200 font-bold">₹{Math.round(basePrice).toLocaleString('en-IN')}</span>
          </div>

          {/* Decomposed Contributing Factors with Visual Bars */}
          {factors.map((factor, idx) => {
            const pct = Math.round(Math.abs(factor.contribution || 0) * 100);
            const isPositive = (factor.contribution || 0) >= 0;
            const barColor = factorColors[idx % factorColors.length];

            return (
              <div key={idx} className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/70 space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-300 font-sans font-medium">{factor.name}</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-400">{typeof factor.value === 'number' ? factor.value.toFixed(2) : factor.value}</span>
                    <span className={`font-bold px-1.5 py-0.2 rounded text-[11px] ${isPositive ? 'bg-teal-950 text-teal-300 border border-teal-800/80' : 'bg-rose-950 text-rose-300 border border-rose-800/80'
                      }`}>
                      {isPositive ? `+${pct}%` : `-${pct}%`}
                    </span>
                  </div>
                </div>

                {/* Progress bar visual */}
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                    style={{ width: `${Math.min(100, Math.max(10, pct * 2.5))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Multilingual Audit Explanation Narrative */}
      <div className="pt-3 border-t border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-300">
            <FileText className="w-3.5 h-3.5 text-teal-400" />
            <span>Operational Audit Narrative</span>
          </div>
          {/* Toggle EN / HI */}
          <div className="flex items-center space-x-1 text-[11px] bg-slate-800 p-0.5 rounded-lg border border-slate-700">
            <button
              onClick={() => setActiveTab('en')}
              className={`px-2 py-0.5 rounded ${activeTab === 'en' ? 'bg-teal-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
            >
              English
            </button>
            <button
              onClick={() => setActiveTab('hi')}
              className={`px-2 py-0.5 rounded ${activeTab === 'hi' ? 'bg-teal-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
            >
              हिन्दी
            </button>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 leading-relaxed min-h-[75px]">
          {activeTab === 'en' ? <p>{explanationEn}</p> : <p className="font-sans leading-relaxed">{explanationHi}</p>}
        </div>
      </div>
    </div>
  );
}

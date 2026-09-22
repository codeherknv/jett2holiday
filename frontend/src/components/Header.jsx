import React from 'react';
import { Plane, Building2, Activity, Globe, Bell, User } from 'lucide-react';

export default function Header({
  selectedEntity,
  setSelectedEntity,
  entities,
  selectedDate,
  setSelectedDate,
  locale,
  setLocale,
  isLive,
  onOpenEventModal,
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Subtitle */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-600 to-teal-400 flex items-center justify-center shadow-lg shadow-teal-500/20">
              <Plane className="w-6 h-6 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-wider text-sm text-teal-400">JETT 2 HOLIDAY</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800 font-mono">
                  APS-02
                </span>
              </div>
              <h1 className="text-sm font-semibold text-slate-200">
                Dynamic Pricing Engine &amp; Revenue Control Plane
              </h1>
            </div>
          </div>

          {/* Quick Actions & Status */}
          <div className="flex items-center space-x-4">
            {/* Live Backend Connection Indicator */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span className="text-slate-300">{isLive ? 'Live API Connected' : 'API Standby (Mock Mode)'}</span>
            </div>

            {/* Emit Event Telemetry Button */}
            <button
              onClick={onOpenEventModal}
              className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-teal-600/20 hover:bg-teal-600/30 text-teal-300 border border-teal-500/30 text-xs font-medium transition-all"
              title="Test POST /events telemetry endpoint"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Emit Event</span>
            </button>

            {/* Multilingual Switcher (EN / HI) */}
            <div className="flex items-center space-x-1 bg-slate-800 p-1 rounded-lg border border-slate-700">
              <button
                onClick={() => setLocale('en-IN')}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  locale === 'en-IN' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                EN
              </button>
              <button
                onClick={() => setLocale('hi')}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  locale === 'hi' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                हिन्दी
              </button>
            </div>

            {/* Profile Avatar */}
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs font-semibold">
              RM
            </div>
          </div>
        </div>

        {/* Subheader Control Bar */}
        <div className="py-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex flex-wrap items-center gap-4">
            {/* Entity Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Room / Flight Entity:</span>
              <select
                value={selectedEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-100 rounded-lg px-3 py-1.5 font-mono focus:outline-none focus:border-teal-500"
              >
                {entities.map((ent) => (
                  <option key={ent.entity_id} value={ent.entity_id}>
                    {ent.entity_name || ent.entity_id} ({ent.entity_type})
                  </option>
                ))}
              </select>
            </div>

            {/* Analysis Window / Date Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Target Stay Date:</span>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-100 rounded-lg px-2.5 py-1.2 font-mono text-xs focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div className="text-slate-400 font-mono">
            Model v4.8 • Refreshed 2m ago (IST)
          </div>
        </div>
      </div>
    </header>
  );
}

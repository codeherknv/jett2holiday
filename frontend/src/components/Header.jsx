import React from 'react';
import { Plane, Building2, Activity, Globe, Sparkles, Calendar, LayoutDashboard, Compass, LogOut, User, Shield, Cpu } from 'lucide-react';

export default function Header({
  selectedEntity,
  setSelectedEntity,
  entities = [],
  selectedDate,
  setSelectedDate,
  locale,
  setLocale,
  isLive,
  onOpenEventModal,
  onOpenModelDiagnostics,
  activeTab = 'admin',
  authRole,
  authUser,
  onLogout,
  t
}) {
  const currentEntity = entities.find((e) => e.entity_id === selectedEntity) || entities[0];
  // Opaque ID treatment: determine flight based purely on entity_type field
  const isFlight = currentEntity?.entity_type === 'flight_fare' || currentEntity?.entity_type === 'flight';

  return (
    <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-xl sticky top-0 z-40 shadow-xl shadow-black/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Subtitle */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-teal-500/25">
              <Plane className="w-5 h-5 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-wider text-sm bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
                  {t ? t('app_title') : 'JETT 2 HOLIDAY'}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800 font-mono font-bold">
                  APS-02
                </span>
              </div>
              <h1 className="text-xs font-semibold text-slate-300">
                {authRole === 'admin'
                  ? (t ? t('app_subtitle') : 'Admin Dynamic Pricing & Bounded Control Plane')
                  : 'Traveller Flight & Hotel Booking Portal'}
              </h1>
            </div>
          </div>

          {/* Active Session & Visible Logout Action */}
          <div className="flex items-center space-x-2">
            <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold ${authRole === 'admin'
                ? 'bg-teal-950/80 text-teal-300 border-teal-800/80'
                : 'bg-indigo-950/80 text-indigo-300 border-indigo-800/80'
              }`}>
              {authRole === 'admin' ? (
                <Shield className="w-3.5 h-3.5 text-teal-400" />
              ) : (
                <User className="w-3.5 h-3.5 text-indigo-400" />
              )}
              <span className="hidden sm:inline">
                {authRole === 'admin' ? 'Admin Manager' : (authUser?.display_name || authUser?.email || 'Traveller')}
              </span>
            </div>

            {/* Logout Button */}
            <button
              onClick={onLogout}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-red-950/60 text-slate-400 hover:text-red-300 border border-slate-800 hover:border-red-800/80 text-xs font-semibold transition"
              title="Logout and return to Portal Selection"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>


          {/* Top Actions & Indicators */}
          <div className="flex items-center space-x-3">
            {/* ML Model Diagnostics Pill */}
            {authRole === 'admin' && (
              <button
                onClick={onOpenModelDiagnostics}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 text-teal-300 border border-teal-800/80 text-xs font-bold transition shadow-sm"
                title="View Hierarchical ML Model Performance & Diagnostics"
              >
                <Cpu className="w-3.5 h-3.5 text-teal-400" />
                <span className="hidden sm:inline">ML Model &bull; 19.97% MAPE</span>
                <span className="sm:hidden">ML Model</span>
              </button>
            )}

            {/* Live Backend Connection Indicator */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-950/80 border border-slate-800 text-xs">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span className="text-slate-300 font-medium hidden sm:inline">
                {isLive ? (t ? t('live_api_connected') : 'Live API Connected') : (t ? t('api_standby') : 'API Standby')}
              </span>
            </div>

            {/* Emit Event Telemetry Button */}
            <button
              onClick={onOpenEventModal}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-teal-600/30 to-emerald-600/30 hover:from-teal-600/40 hover:to-emerald-600/40 text-teal-300 border border-teal-500/40 text-xs font-bold transition shadow-sm"
              title="Test POST /events telemetry endpoint"
            >
              <Activity className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden sm:inline">{t ? t('emit_event') : 'Emit Event'}</span>
            </button>

            {/* Multilingual Switcher (EN / HI) */}
            <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setLocale('en-IN')}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${locale === 'en-IN' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
              >
                EN
              </button>
              <button
                onClick={() => setLocale('hi')}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${locale === 'hi' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
              >
                हिन्दी
              </button>
            </div>
          </div>
        </div>

        {/* Subheader Control Bar (only when in Admin view) */}
        {activeTab === 'admin' && (
          <div className="py-2.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              {/* Entity Selector with Icon */}
              <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1 rounded-xl border border-slate-800">
                {isFlight ? (
                  <Plane className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                ) : (
                  <Building2 className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                )}
                <span className="text-slate-400 font-medium">{t ? t('entity') : 'Entity'}:</span>
                <select
                  value={selectedEntity}
                  onChange={(e) => setSelectedEntity(e.target.value)}
                  className="bg-transparent text-slate-100 font-mono font-medium focus:outline-none cursor-pointer text-xs"
                >
                  {entities.map((ent) => (
                    <option key={ent.entity_id} value={ent.entity_id} className="bg-slate-900 text-slate-100">
                      {ent.entity_name || ent.entity_id}
                    </option>
                  ))}
                </select>
              </div>

              {/* Analysis Date Selector */}
              <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1 rounded-xl border border-slate-800">
                <Calendar className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                <span className="text-slate-400 font-medium">{t ? t('target_stay_date') : 'Target Stay Date'}:</span>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="bg-transparent text-slate-100 font-mono font-medium text-xs focus:outline-none cursor-pointer"
                />
              </div>
            </div>

            <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
              <span>APS-02 Deterministic Bounded Engine Active</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

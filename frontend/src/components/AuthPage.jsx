import React, { useState } from 'react';
import { Plane, Shield, KeyRound, User, Lock, Mail, ArrowRight, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';
import { adminLogin, travellerLogin, travellerSignup } from '../api/client';

export default function AuthPage({ onAuthSuccess, locale = 'en-IN', t }) {
  // Mode selection: 'choose' | 'admin' | 'traveller_login' | 'traveller_signup'
  const [selectedPath, setSelectedPath] = useState(null); // 'admin' | 'traveller'

  // Admin form state
  const [adminUsername, setAdminUsername] = useState('admin');
  const [adminPassword, setAdminPassword] = useState('admin@123');
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState(null);

  // Traveller form state
  const [travellerMode, setTravellerMode] = useState('login'); // 'login' | 'signup'
  const [travellerEmail, setTravellerEmail] = useState('');
  const [travellerPassword, setTravellerPassword] = useState('');
  const [travellerName, setTravellerName] = useState('');
  const [travellerLoading, setTravellerLoading] = useState(false);
  const [travellerError, setTravellerError] = useState(null);

  const handleAdminSubmit = async (e) => {
    e.preventDefault();
    setAdminLoading(true);
    setAdminError(null);
    try {
      const res = await adminLogin(adminUsername, adminPassword);
      if (onAuthSuccess) {
        onAuthSuccess('admin', res);
      }
    } catch (err) {
      setAdminError(err.message || 'Invalid admin credentials');
    } finally {
      setAdminLoading(false);
    }
  };

  const handleTravellerSubmit = async (e) => {
    e.preventDefault();
    setTravellerLoading(true);
    setTravellerError(null);
    try {
      let res;
      if (travellerMode === 'signup') {
        if (!travellerName.trim()) {
          throw new Error('Please enter your full name');
        }
        res = await travellerSignup(travellerEmail, travellerPassword, travellerName);
      } else {
        res = await travellerLogin(travellerEmail, travellerPassword);
      }
      if (onAuthSuccess) {
        onAuthSuccess('traveller', res);
      }
    } catch (err) {
      setTravellerError(err.message || 'Authentication failed');
    } finally {
      setTravellerLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-teal-500 selection:text-white">
      {/* Top Banner */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-teal-500/20">
            <Plane className="w-5 h-5 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold tracking-wider text-sm bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
                JETT 2 HOLIDAY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800 font-mono font-bold">
                APS-02
              </span>
            </div>
            <p className="text-xs text-slate-400">Real-Time Dynamic Pricing & Demand Forecasting Platform</p>
          </div>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Security Gateway &bull; Role-Gated Portal
        </div>
      </header>

      {/* Main Choice Screen */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-12 flex flex-col justify-center">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            Select Your Portal Access
          </h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Choose your destination experience. Authentication is strictly segregated between administrative revenue optimization and customer reservations.
          </p>
        </div>

        {/* Dual Portal Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">

          {/* ========================================== */}
          {/* Path 1: Admin Control Plane */}
          {/* ========================================== */}
          <div className={`rounded-2xl border transition-all duration-200 bg-slate-900/60 backdrop-blur-xl p-6 sm:p-8 flex flex-col justify-between shadow-xl ${selectedPath === 'admin'
              ? 'border-teal-500/80 ring-2 ring-teal-500/30 shadow-teal-950/40'
              : 'border-slate-800 hover:border-slate-700'
            }`}>
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-teal-950 border border-teal-800/80 flex items-center justify-center text-teal-400">
                  <Shield className="w-6 h-6" />
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-teal-950/80 text-teal-300 border border-teal-800/50">
                  Restricted Demo
                </span>
              </div>

              <h3 className="text-lg font-bold text-white mb-1">Admin Dynamic Pricing Engine</h3>
              <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                Autonomous bounded dynamic pricing, 30-day forecast curves, guardrail clamp diagnostics, ML factor explainability, and What-If revenue simulations.
              </p>

              {/* Admin Form */}
              <form onSubmit={handleAdminSubmit} className="space-y-4">
                {adminError && (
                  <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/60 text-xs text-red-300 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <span>{adminError}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Username</label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={adminUsername}
                      onChange={(e) => setAdminUsername(e.target.value)}
                      required
                      placeholder="admin"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="password"
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                    />
                  </div>
                </div>

                <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-2.5 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Hackathon Demo Account:</span>
                  <span className="font-mono text-teal-400 font-semibold">admin / admin@123</span>
                </div>

                <button
                  type="submit"
                  disabled={adminLoading}
                  onClick={() => setSelectedPath('admin')}
                  className="w-full mt-2 flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white text-xs font-bold transition shadow-lg shadow-teal-900/30 disabled:opacity-50"
                >
                  <span>{adminLoading ? 'Verifying Admin Token...' : 'Enter Admin Control Plane'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>


          {/* ========================================== */}
          {/* Path 2: Traveller Booking Portal */}
          {/* ========================================== */}
          <div className={`rounded-2xl border transition-all duration-200 bg-slate-900/60 backdrop-blur-xl p-6 sm:p-8 flex flex-col justify-between shadow-xl ${selectedPath === 'traveller'
              ? 'border-indigo-500/80 ring-2 ring-indigo-500/30 shadow-indigo-950/40'
              : 'border-slate-800 hover:border-slate-700'
            }`}>
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-indigo-950 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
                  <Plane className="w-6 h-6" />
                </div>
                <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
                  <button
                    type="button"
                    onClick={() => { setTravellerMode('login'); setTravellerError(null); }}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition ${travellerMode === 'login' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                      }`}
                  >
                    Log In
                  </button>
                  <button
                    type="button"
                    onClick={() => { setTravellerMode('signup'); setTravellerError(null); }}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition ${travellerMode === 'signup' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                      }`}
                  >
                    Sign Up
                  </button>
                </div>
              </div>

              <h3 className="text-lg font-bold text-white mb-1">
                {travellerMode === 'signup' ? 'Create Traveller Account' : 'Traveller Booking Portal'}
              </h3>
              <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                Live flight & hotel availability search, real-time dynamic pricing transparency badges, and instant booking confirmations recorded to inventory calendar.
              </p>

              {/* Traveller Form */}
              <form onSubmit={handleTravellerSubmit} className="space-y-4">
                {travellerError && (
                  <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/60 text-xs text-red-300 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <span>{travellerError}</span>
                  </div>
                )}

                {travellerMode === 'signup' && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                    <div className="relative">
                      <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                      <input
                        type="text"
                        value={travellerName}
                        onChange={(e) => setTravellerName(e.target.value)}
                        required
                        placeholder="e.g. Rohan Sharma"
                        className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="email"
                      value={travellerEmail}
                      onChange={(e) => setTravellerEmail(e.target.value)}
                      required
                      placeholder="traveler@example.com"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="password"
                      value={travellerPassword}
                      onChange={(e) => setTravellerPassword(e.target.value)}
                      required
                      placeholder="Min 6 characters (bcrypt encrypted)"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-600 outline-none transition"
                    />
                  </div>
                </div>

                <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-2.5 text-[11px] text-slate-400">
                  {travellerMode === 'signup'
                    ? 'New account credentials will be hashed using pure bcrypt.'
                    : 'Log in with any registered account or switch to Sign Up above.'}
                </div>

                <button
                  type="submit"
                  disabled={travellerLoading}
                  onClick={() => setSelectedPath('traveller')}
                  className="w-full mt-2 flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-bold transition shadow-lg shadow-indigo-900/30 disabled:opacity-50"
                >
                  <span>
                    {travellerLoading
                      ? 'Authenticating...'
                      : travellerMode === 'signup'
                        ? 'Create Account & Enter Portal'
                        : 'Enter Traveller Portal'}
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 px-6 py-4 text-center text-xs text-slate-500 font-mono">
        &copy; 2026 JETT 2 HOLIDAY &bull; APS-02 Hackathon Project &bull; Team Jett 2 Holiday
      </footer>
    </div>
  );
}

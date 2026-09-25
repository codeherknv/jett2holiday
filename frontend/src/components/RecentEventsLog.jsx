import React from 'react';
import { Activity, ShieldAlert, ShoppingBag, Search, Eye, ArrowUpRight, Zap } from 'lucide-react';

export default function RecentEventsLog({ events = [], onOpenEventModal }) {
  const defaultEvents = [
    {
      id: 'evt_1727167200_8921',
      type: 'booking',
      entity_id: 'rmt_ca391f47',
      label: 'Deluxe Suite Booking Confirmed',
      channel: 'Direct Web',
      price: '₹5,051.69',
      lead_time: '14 days',
      time: 'Just now',
      clamped: false,
    },
    {
      id: 'evt_1727167140_3412',
      type: 'clamp_alert',
      entity_id: 'rmt_ca391f47',
      label: 'Guardrail Clamp: Ceiling Limit Enforced',
      channel: 'Pricing Engine',
      price: '₹6,130.68 (Capped from ₹7,450)',
      lead_time: '7 days',
      time: '2m ago',
      clamped: true,
    },
    {
      id: 'evt_1727167080_1109',
      type: 'search',
      entity_id: 'far_5a8bce18',
      label: 'Flight Route Search (DEL -> SXR)',
      channel: 'Mobile App',
      price: '₹4,850.00',
      lead_time: '21 days',
      time: '5m ago',
      clamped: false,
    },
    {
      id: 'evt_1727166920_7741',
      type: 'view',
      entity_id: 'rmt_ca391f47',
      label: 'Property Page View & Availability Check',
      channel: 'Direct Web',
      price: '₹5,051.69',
      lead_time: '10 days',
      time: '8m ago',
      clamped: false,
    },
  ];

  const displayList = events.length > 0 ? events : defaultEvents;

  const getIcon = (type) => {
    switch (type) {
      case 'booking':
        return <ShoppingBag className="w-4 h-4 text-emerald-400" />;
      case 'clamp_alert':
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case 'search':
        return <Search className="w-4 h-4 text-blue-400" />;
      case 'view':
      default:
        return <Eye className="w-4 h-4 text-teal-400" />;
    }
  };

  const getBadgeStyle = (type) => {
    switch (type) {
      case 'booking':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
      case 'clamp_alert':
        return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
      case 'search':
        return 'bg-blue-950/80 text-blue-300 border-blue-800/80';
      case 'view':
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="glass-panel p-5 mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Live Telemetry &amp; Dynamic Pricing Audit Stream
            </h3>
            <p className="text-xs text-slate-400">
              Real-time ingestion of searches, bookings, cancellations, and guardrail clamping decisions
            </p>
          </div>
        </div>

        <button
          onClick={onOpenEventModal}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-teal-600/20 hover:bg-teal-600/30 text-teal-300 border border-teal-500/30 text-xs font-semibold transition"
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Emit Telemetry Event</span>
        </button>
      </div>

      {/* Events Table / Stream */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
              <th className="pb-2 font-semibold">Event Type</th>
              <th className="pb-2 font-semibold">Description</th>
              <th className="pb-2 font-semibold">Entity ID</th>
              <th className="pb-2 font-semibold">Channel</th>
              <th className="pb-2 font-semibold">Quoted / Published</th>
              <th className="pb-2 font-semibold">Lead Time</th>
              <th className="pb-2 font-semibold text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {displayList.map((item, idx) => (
              <tr key={item.id || idx} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-2.5">
                  <span
                    className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${getBadgeStyle(
                      item.type
                    )}`}
                  >
                    {getIcon(item.type)}
                    <span className="capitalize ml-1">{item.type.replace('_', ' ')}</span>
                  </span>
                </td>
                <td className="py-2.5 font-sans font-medium text-slate-200">{item.label}</td>
                <td className="py-2.5 text-teal-400">{item.entity_id}</td>
                <td className="py-2.5 text-slate-400">{item.channel}</td>
                <td className="py-2.5 text-slate-200 font-semibold">{item.price}</td>
                <td className="py-2.5 text-slate-400">{item.lead_time}</td>
                <td className="py-2.5 text-slate-500 text-right">{item.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

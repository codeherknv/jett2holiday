import React, { useState, useEffect } from 'react';
import {
  Calendar,
  ShieldCheck,
  CheckCircle2,
  ShoppingBag,
  Sparkles,
  Building2,
  AlertTriangle,
  ArrowRight,
  UserCheck,
  Loader2,
  RefreshCw,
  AlertCircle,
  XCircle,
} from 'lucide-react';
import { logEvent, fetchTravellerSearch } from '../api/client';

export default function TravellerPortal({
  selectedDate,
  onBookingConfirmed,
  locale = 'en-IN',
  t,
}) {
  const [date, setDate] = useState(selectedDate || '2026-10-15');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bookingSuccess, setBookingSuccess] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);
  const [isFallback, setIsFallback] = useState(false);
  const [bookingEntityId, setBookingEntityId] = useState(null);

  const fetchCatalog = async (targetDate) => {
    setLoading(true);
    try {
      const data = await fetchTravellerSearch(targetDate);
      setItems(data);
      setIsFallback(false);
    } catch (err) {
      console.warn('Live search failed, loading fallback preview catalog:', err);
      setIsFallback(true);

      // Local fallback
      setItems([
        {
          entity_id: 'rmt_ca391f47',
          entity_name: 'Villa Mahal Resort (Deluxe Heritage Room)',
          entity_type: 'room_type',
          date: targetDate,
          total_units: 10,
          booked_units: 8,
          available_units: 2,
          occupancy_pct: 80,
          base_price: 3698,
          dynamic_price: 4850,
          bound_clamped: false,
          badge_context: 'Peak Autumn Season • 80% Booked',
          badge_color: 'amber',
        },
        {
          entity_id: 'rmt_6b804d20',
          entity_name: 'Hillview Regency Suites (Lake View Suite)',
          entity_type: 'room_type',
          date: targetDate,
          total_units: 15,
          booked_units: 9,
          available_units: 6,
          occupancy_pct: 60,
          base_price: 4200,
          dynamic_price: 4950,
          bound_clamped: true,
          badge_context: 'Protected Price • Capped by Ceiling Guardrail',
          badge_color: 'emerald',
        },
        {
          entity_id: 'far_5a8bce18',
          entity_name: 'Air India AI-7050 (Economy Class)',
          entity_type: 'flight_fare',
          date: targetDate,
          total_units: 20,
          booked_units: 14,
          available_units: 6,
          occupancy_pct: 70,
          base_price: 5500,
          dynamic_price: 6400,
          bound_clamped: false,
          badge_context: 'High Availability • 6 Seats Left',
          badge_color: 'teal',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog(date);
  }, [date]);

  const handleBook = async (item) => {
    setBookingEntityId(item.entity_id);
    setErrorBanner(null);
    try {
      const now = new Date().toISOString();
      await logEvent(item.entity_id, 'booking', now, 14, date);
      setBookingSuccess({
        entityName: item.entity_name,
        price: item.dynamic_price,
        date: date,
      });

      // If live backend is connected, refresh catalog to get true DB counts;
      // otherwise decrement locally
      if (!isFallback) {
        await fetchCatalog(date);
      } else {
        setItems((prev) =>
          prev.map((i) =>
            i.entity_id === item.entity_id
              ? {
                ...i,
                available_units: Math.max(0, i.available_units - 1),
                booked_units: i.booked_units + 1,
              }
              : i
          )
        );
      }

      if (onBookingConfirmed) {
        onBookingConfirmed({
          type: 'booking',
          entity_id: item.entity_id,
          label: `${item.entity_name} Confirmed Reservation`,
          price: `₹${item.dynamic_price.toLocaleString('en-IN')}`,
          channel: 'Direct Traveller Booking',
          lead_time: '14 days',
          time: 'Just now',
        });
      }

      setTimeout(() => {
        setBookingSuccess(null);
      }, 4000);
    } catch (err) {
      console.error('Booking failed:', err);
      if (err.status === 409 || err.message?.toLowerCase().includes('sold out')) {
        setErrorBanner({
          type: 'warning',
          title: 'Unit Sold Out',
          message: 'This unit is sold out for your selected dates.',
        });
      } else if (err.status === 401 || err.status === 403) {
        setErrorBanner({
          type: 'error',
          title: 'Authentication Required',
          message: 'Your session has expired or you do not have permission. Please log in again.',
        });
      } else {
        setErrorBanner({
          type: 'error',
          title: 'Reservation Failed',
          message:
            err.message ||
            'An unexpected error occurred while processing your booking. Please try again.',
        });
      }
    } finally {
      setBookingEntityId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel p-6 bg-gradient-to-r from-slate-900 via-teal-950/40 to-slate-900 border border-teal-500/30">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-teal-400 text-xs font-bold uppercase tracking-wider mb-1">
              <Sparkles className="w-4 h-4" />
              <span>
                {t
                  ? t('traveller_portal_heading')
                  : 'Live Availability & Transparent Dynamic Pricing'}
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-100">
              {locale === 'hi'
                ? 'सुरक्षित एवं पारदर्शी अवकाश बुकिंग'
                : 'Fair, Safe & Bounded Travel Booking'}
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              {t
                ? t('traveller_portal_sub')
                : 'Every price is bounded by strict profitability floors and anti-surge ceilings. Transparent badges explain real-time market conditions.'}
            </p>
          </div>

          {/* Date Picker */}
          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800">
            <Calendar className="w-4 h-4 text-teal-400" />
            <span className="text-xs text-slate-400 font-medium">Select Travel Date:</span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="bg-transparent text-slate-100 font-mono text-xs focus:outline-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Fallback Notice Banner */}
      {isFallback && (
        <div className="p-4 rounded-xl bg-amber-950/80 border border-amber-800 text-amber-200 text-xs flex items-center justify-between shadow-lg">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <span className="font-bold text-amber-300">Notice: Viewing Fallback Catalog Data</span>
              <p className="text-amber-200/80 mt-0.5">
                Live rates and inventory could not be reached for {date}. You are currently viewing cached preview data, not live availability.
              </p>
            </div>
          </div>
          <button
            onClick={() => fetchCatalog(date)}
            className="ml-4 px-3 py-1.5 rounded-lg bg-amber-900/80 hover:bg-amber-800 text-amber-200 font-semibold border border-amber-700/60 flex items-center space-x-1.5 transition shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Live Search</span>
          </button>
        </div>
      )}

      {/* Error / Sold Out Alert Banner */}
      {errorBanner && (
        <div
          className={`p-4 rounded-xl flex items-start justify-between shadow-xl animate-in fade-in duration-200 ${errorBanner.type === 'warning'
              ? 'bg-amber-950/90 border border-amber-700 text-amber-200'
              : 'bg-rose-950/90 border border-rose-800 text-rose-200'
            }`}
        >
          <div className="flex items-start space-x-3">
            {errorBanner.type === 'warning' ? (
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div>
              <h4 className="font-bold text-sm tracking-wide">{errorBanner.title}</h4>
              <p className="text-xs mt-0.5 opacity-90">{errorBanner.message}</p>
            </div>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-slate-400 hover:text-slate-200 text-xs font-mono ml-3 px-2 py-1 rounded bg-slate-900/60 border border-slate-700 hover:border-slate-500"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Booking Confirmation Toast / Banner */}
      {bookingSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/90 border border-emerald-800 text-emerald-200 text-sm flex items-center justify-between shadow-xl animate-in fade-in duration-200">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <span className="font-bold">Reservation Confirmed!</span>
              <p className="text-xs text-emerald-300 mt-0.5">
                Successfully booked {bookingSuccess.entityName} on {bookingSuccess.date} for ₹
                {Math.round(bookingSuccess.price).toLocaleString('en-IN')}. Inventory units updated.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Item Cards Grid */}
      {loading ? (
        <div className="py-12 text-center text-slate-400 text-sm font-mono">
          Loading live rates and transparent badges from FastAPI...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item) => {
            const isClamped = item.bound_clamped;
            return (
              <div
                key={item.entity_id}
                className="glass-panel p-5 flex flex-col justify-between hover:border-teal-500/40 transition duration-200 relative overflow-hidden group"
              >
                {/* Badge Context Pill */}
                <div className="mb-3">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${item.badge_color === 'amber'
                        ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                        : item.badge_color === 'emerald'
                          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                          : 'bg-teal-950/80 text-teal-300 border-teal-800'
                      }`}
                  >
                    {item.badge_context}
                  </span>
                </div>

                {/* Title */}
                <div>
                  <h3 className="font-bold text-slate-100 text-base group-hover:text-teal-300 transition">
                    {item.entity_name}
                  </h3>
                  <div className="flex items-center space-x-2 text-xs text-slate-400 mt-1 font-mono">
                    <span className="capitalize">{item.entity_type?.replace('_', ' ')}</span>
                    <span>&bull;</span>
                    <span className="text-teal-400 font-semibold">{item.available_units} units left</span>
                  </div>
                </div>

                {/* Price Display */}
                <div className="my-5 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
                      Published Rate
                    </span>
                    <div className="text-2xl font-black font-mono text-teal-300">
                      ₹{Math.round(item.dynamic_price).toLocaleString('en-IN')}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 block">Baseline</span>
                    <span className="text-xs text-slate-400 font-mono line-through">
                      ₹{Math.round(item.base_price).toLocaleString('en-IN')}
                    </span>
                  </div>
                </div>

                {/* Safety Guarantee Footnote */}
                <div className="text-[11px] text-slate-400 flex items-center space-x-1.5 mb-4">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span>Bounded by Jett 2 Holiday Anti-Surge Guardrails</span>
                </div>

                {/* Book Action */}
                <button
                  onClick={() => handleBook(item)}
                  disabled={item.available_units <= 0 || bookingEntityId === item.entity_id}
                  className="w-full py-2.5 px-4 rounded-xl bg-teal-600 hover:bg-teal-500 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs transition flex items-center justify-center space-x-2 shadow-lg shadow-teal-600/20"
                >
                  {bookingEntityId === item.entity_id ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Reserving...</span>
                    </>
                  ) : (
                    <>
                      <ShoppingBag className="w-3.5 h-3.5" />
                      <span>{item.available_units > 0 ? (t ? t('book_now') : 'Book Now') : 'Sold Out'}</span>
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

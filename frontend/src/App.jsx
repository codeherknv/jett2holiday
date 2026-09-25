import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricsRow from './components/MetricsRow';
import ForecastChart from './components/ForecastChart';
import ExplainabilityCard from './components/ExplainabilityCard';
import SimulatorCard from './components/SimulatorCard';
import EventModal from './components/EventModal';
import ClampInspectorModal from './components/ClampInspectorModal';
import ManualOverrideModal from './components/ManualOverrideModal';
import RecentEventsLog from './components/RecentEventsLog';
import TravellerPortal from './components/TravellerPortal';
import AuthPage from './components/AuthPage';
import ModelDiagnosticsModal from './components/ModelDiagnosticsModal';
import translations from './i18n.json';
import {
  calculatePricing,
  explainPricing,
  simulatePricing,
  checkBackendHealth,
  fetchEntities,
  fetchForecastHorizon,
  fetchForecasterMetrics,
  getAuthToken,
  getAuthRole,
  getAuthUser,
  clearAuthSession,
} from './api/client';


// Generate default 30-day forecast curve with dynamic entity bounds and date responsiveness
function generateDefaultForecast(startDateStr = '2026-10-15', baseMultiplier = 1.0, entityMeta = null) {
  const startDate = new Date(startDateStr || '2026-10-15');
  const items = [];
  const baseFare = entityMeta?.base_price || 3698;
  const floorPrice = entityMeta?.floor_price || 2485;
  const ceilingPrice = entityMeta?.ceiling_price || 6131;

  for (let i = 0; i < 30; i++) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().split('T')[0];

    // Responsive Day of week cycle: weekend lift
    const dow = d.getDay();
    const dowMult = dow === 5 || dow === 6 ? 1.25 : (dow === 2 ? 0.90 : 1.0);
    const leadFactor = 1.0 + 0.18 * Math.exp(-0.06 * i);
    const demandIndex = Number(Math.max(0.7, Math.min(2.1, 1.0 + (dowMult - 1.0) * 0.7 + (leadFactor - 1.0) * 0.4)).toFixed(2));
    const rawCandidate = Math.round(baseFare * (1.0 + (demandIndex - 1.0) * 0.75) * baseMultiplier);
    
    let clamped = false;
    let clampedBy = null;
    let boundName = null;
    let boundValue = null;
    let effective = rawCandidate;

    if (rawCandidate > ceilingPrice) {
      clamped = true;
      clampedBy = 'ceiling';
      boundName = `Ceiling Guardrail (₹${Math.round(ceilingPrice).toLocaleString('en-IN')})`;
      boundValue = ceilingPrice;
      effective = ceilingPrice;
    } else if (rawCandidate < floorPrice) {
      clamped = true;
      clampedBy = 'floor';
      boundName = `Floor Guardrail (₹${Math.round(floorPrice).toLocaleString('en-IN')})`;
      boundValue = floorPrice;
      effective = floorPrice;
    }

    items.push({
      date: dateStr,
      base_price: baseFare,
      raw_model_price: rawCandidate,
      current_dynamic_price: effective,
      simulated_price: effective,
      demand_index: demandIndex,
      floor_price: floorPrice,
      ceiling_price: ceilingPrice,
      clamped,
      clamped_by: clampedBy,
      bound_name: boundName,
      bound_value: boundValue,
      factors: [
        { name: 'Demand Index (forecast)', value: demandIndex, contribution: Math.round((demandIndex - 1) * 35) / 100 },
        { name: 'Occupancy Factor', value: 1.15, contribution: 0.15 },
        { name: 'Seasonality Multiplier', value: 1.18, contribution: 0.18 }
      ]
    });
  }
  return items;
}

export default function App() {
  // Authentication & Session state
  const [authRole, setAuthRole] = useState(() => getAuthRole());
  const [authUser, setAuthUser] = useState(() => getAuthUser());
  const [locale, setLocale] = useState('en-IN');
  const t = (key) => translations[locale]?.[key] || translations['en-IN']?.[key] || key;

  const handleAuthSuccess = (role, data) => {
    setAuthRole(role);
    setAuthUser(data);
  };

  const handleLogout = () => {
    clearAuthSession();
    setAuthRole(null);
    setAuthUser(null);
  };


  // State variables
  const [entities, setEntities] = useState([
    {
      entity_id: 'rmt_ca391f47',
      entity_name: 'Villa Mahal Resort Deluxe Room [rmt_ca391f47]',
      entity_type: 'room_type',
      floor_price: 2485.41,
      ceiling_price: 6130.68,
      max_daily_move_pct: 0.15,
      base_price: 3697.89,
    },
    {
      entity_id: 'far_5a8bce18',
      entity_name: 'UL-9879 Saver Economy Fare [far_5a8bce18]',
      entity_type: 'flight_fare',
      floor_price: 3200.0,
      ceiling_price: 9500.0,
      max_daily_move_pct: 0.20,
      base_price: 5500.0,
    },
  ]);

  const [selectedEntity, setSelectedEntity] = useState('rmt_ca391f47');
  const [selectedDate, setSelectedDate] = useState('2026-10-15');
  const [isLive, setIsLive] = useState(false);
  
  // Modals state
  const [isEventModalOpen, setIsEventModalOpen] = useState(false);
  const [isClampInspectorOpen, setIsClampInspectorOpen] = useState(false);
  const [inspectedPointData, setInspectedPointData] = useState(null);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overrideDateTarget, setOverrideDateTarget] = useState('2026-10-15');
  const [isModelDiagnosticsOpen, setIsModelDiagnosticsOpen] = useState(false);
  const [forecasterMetrics, setForecasterMetrics] = useState(null);

  // Dynamic Pricing & Explainability State
  const [pricingData, setPricingData] = useState({
    effective_price: 4350.00,
    base_price: 3697.89,
    demand_index: 1.44,
    occupancy_factor: 1.06,
    lead_time_factor: 1.02,
    seasonality_factor: 1.18,
    competitor_factor: 1.15,
    bound_clamped: false,
  });

  const [explainData, setExplainData] = useState(null);

  // Simulation & Horizon State
  const [baseMultiplier, setBaseMultiplier] = useState(1.15);
  const [dailyMoveLimit, setDailyMoveLimit] = useState(0.20);
  const [isSimulating, setIsSimulating] = useState(false);
  const [hasSimulated, setHasSimulated] = useState(true);
  const [simulationResults, setSimulationResults] = useState({
    revenue_delta_pct: 12.4,
    booking_rate_delta_pct: -2.1,
    breaches: 4,
  });
  const currentEntityMeta = entities.find((e) => e.entity_id === selectedEntity) || entities[0];
  const [forecastCurve, setForecastCurve] = useState(() => generateDefaultForecast('2026-10-15', 1.15, entities[0]));

  // Live Telemetry Event Stream State
  const [recentEvents, setRecentEvents] = useState([
    {
      id: 'evt_init_1',
      type: 'booking',
      entity_id: 'rmt_ca391f47',
      label: 'Deluxe Room Booking Confirmed (₹4,350.00)',
      channel: 'Direct Web',
      price: '₹4,350.00',
      lead_time: '14 days',
      time: 'Just now',
    },
    {
      id: 'evt_init_2',
      type: 'clamp_alert',
      entity_id: 'rmt_ca391f47',
      label: 'Guardrail Enforcement: Ceiling Limit Clamped',
      channel: 'Pricing Engine',
      price: '₹6,130.68 (Saved ₹1,319)',
      lead_time: '7 days',
      time: '2m ago',
    },
    {
      id: 'evt_init_3',
      type: 'search',
      entity_id: 'far_5a8bce18',
      label: 'Flight Route Search (DEL -> SXR)',
      channel: 'Mobile App',
      price: '₹4,850.00',
      lead_time: '21 days',
      time: '4m ago',
    }
  ]);

  // 1. Initial Load & Backend Healthcheck
  useEffect(() => {
    async function init() {
      try {
        const health = await checkBackendHealth();
        if (health.status === 'healthy') {
          setIsLive(true);
          if (authRole === 'admin') {
            const [entityList, fMetrics] = await Promise.all([
              fetchEntities().catch(() => null),
              fetchForecasterMetrics().catch(() => null)
            ]);
            if (fMetrics) setForecasterMetrics(fMetrics);
            if (entityList?.length) {
              setEntities(entityList);
              if (!entityList.some(e => e.entity_id === selectedEntity)) {
                setSelectedEntity(entityList[0].entity_id);
              }
            }
          }
        }
      } catch (err) {
        if (err.status === 401 || err.status === 403) {
          handleLogout();
        }
        setIsLive(false);
      }
    }
    init();
  }, [authRole]);

  // 2. Fetch Pricing, Explainability, and 30-Day Horizon when entity or date changes
  const fetchAllData = async () => {
    if (authRole !== 'admin') return;
    try {
      const [pData, eData, hData] = await Promise.all([
        calculatePricing(selectedEntity, selectedDate),
        explainPricing(selectedEntity, selectedDate),
        fetchForecastHorizon(selectedEntity, selectedDate).catch(() => null)
      ]);

      setPricingData(pData);
      setExplainData(eData);

      if (hData?.simulated_price_curve?.length) {
        setForecastCurve(hData.simulated_price_curve);
        setSimulationResults({
          revenue_delta_pct: hData.revenue_delta_pct,
          booking_rate_delta_pct: hData.booking_rate_delta_pct,
          breaches: hData.breaches,
        });
      }
      setIsLive(true);
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        handleLogout();
        return;
      }
      // Fallback to local responsive curve using selected date and active entity bounds
      setForecastCurve(generateDefaultForecast(selectedDate, baseMultiplier, currentEntityMeta));
    }
  };

  useEffect(() => {
    if (authRole === 'admin') {
      fetchAllData();
    }
  }, [selectedEntity, selectedDate, authRole]);


  // 3. Handle Running Simulation (Calls POST /pricing/simulate)
  const handleRunSimulation = async (multOverride, moveOverride) => {
    const mult = typeof multOverride === 'number' ? multOverride : baseMultiplier;
    const move = typeof moveOverride === 'number' ? moveOverride : dailyMoveLimit;
    setIsSimulating(true);
    try {
      const res = await simulatePricing(selectedEntity, mult, move, selectedDate);
      setSimulationResults({
        revenue_delta_pct: res.revenue_delta_pct,
        booking_rate_delta_pct: res.booking_rate_delta_pct,
        breaches: res.breaches,
      });
      if (res.simulated_price_curve?.length) {
        setForecastCurve(res.simulated_price_curve);
      }
      setHasSimulated(true);
      setIsLive(true);
    } catch (err) {
      console.warn("Simulation call fallback:", err);
      const newCurve = generateDefaultForecast(selectedDate, mult, currentEntityMeta);
      setForecastCurve(newCurve);
      setSimulationResults({
        revenue_delta_pct: Number(((mult - 1.0) * 82.5).toFixed(1)),
        booking_rate_delta_pct: Number((-(mult - 1.0) * 14.0).toFixed(1)),
        breaches: mult > 1.3 ? 6 : 2,
      });
      setHasSimulated(true);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleResetSimulation = async () => {
    setBaseMultiplier(1.0);
    setDailyMoveLimit(0.15);
    setHasSimulated(false);
    setIsSimulating(true);
    try {
      const hData = await fetchForecastHorizon(selectedEntity);
      if (hData?.simulated_price_curve?.length) {
        setForecastCurve(hData.simulated_price_curve);
        setSimulationResults({
          revenue_delta_pct: 0.0,
          booking_rate_delta_pct: 0.0,
          breaches: hData.breaches || 0,
        });
      }
    } catch {
      setForecastCurve(generateDefaultForecast(1.0));
      setSimulationResults({
        revenue_delta_pct: 0.0,
        booking_rate_delta_pct: 0.0,
        breaches: 0,
      });
    } finally {
      setIsSimulating(false);
    }
  };

  // Inspect specific point
  const handleInspectPoint = (pointData) => {
    setInspectedPointData(pointData);
    setIsClampInspectorOpen(true);
  };

  // Open override modal
  const handleOpenOverride = (pointData) => {
    if (pointData?.date) {
      setOverrideDateTarget(pointData.date);
    }
    setIsOverrideModalOpen(true);
  };

  // Handle applied override
  const handleOverrideApplied = (overrideRes) => {
    setForecastCurve((prev) =>
      prev.map((pt) => {
        if (pt.date === overrideRes.date) {
          return {
            ...pt,
            simulated_price: overrideRes.override_price,
            current_dynamic_price: overrideRes.override_price,
            clamped: false,
          };
        }
        return pt;
      })
    );
    if (overrideRes.date === selectedDate) {
      setPricingData((prev) => ({
        ...prev,
        effective_price: overrideRes.override_price,
      }));
    }
    // Append to live audit events stream
    setRecentEvents((prev) => [
      {
        id: `evt_override_${Date.now()}`,
        type: 'clamp_alert',
        entity_id: selectedEntity,
        label: `Manual Override Applied: ₹${overrideRes.override_price.toLocaleString('en-IN')}`,
        channel: 'Admin Override',
        price: `₹${overrideRes.override_price.toLocaleString('en-IN')}`,
        lead_time: overrideRes.date,
        time: 'Just now',
      },
      ...prev,
    ]);
  };

  // Handle live event emitted from modal or traveller flow
  const handleEventEmitted = (eventPayload) => {
    setRecentEvents((prev) => [
      {
        id: `evt_${Date.now()}`,
        type: eventPayload.type,
        entity_id: eventPayload.entity_id,
        label: eventPayload.label || `Live ${eventPayload.type.toUpperCase()} Telemetry Ingested`,
        channel: eventPayload.channel || 'Direct Web',
        price: eventPayload.price || `₹${pricingData.effective_price.toLocaleString('en-IN')}`,
        lead_time: `${eventPayload.lead_time_days || 14} days`,
        time: 'Just now',
      },
      ...prev,
    ]);
    // Refresh calculations reactively
    fetchAllData();
  };

  // Route Guard: If not authenticated, render Auth Choice Screen
  if (!authRole || !getAuthToken()) {
    return (
      <AuthPage
        onAuthSuccess={handleAuthSuccess}
        locale={locale}
        t={t}
      />
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Navigation */}
      <Header
        selectedEntity={selectedEntity}
        setSelectedEntity={setSelectedEntity}
        entities={entities}
        selectedDate={selectedDate}
        setSelectedDate={setSelectedDate}
        locale={locale}
        setLocale={setLocale}
        isLive={isLive}
        onOpenEventModal={() => setIsEventModalOpen(true)}
        onOpenModelDiagnostics={() => setIsModelDiagnosticsOpen(true)}
        activeTab={authRole}
        authRole={authRole}
        authUser={authUser}
        onLogout={handleLogout}
        t={t}
      />

      {/* Main Control Plane / Traveller Portal View */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {authRole === 'traveller' ? (
          /* Traveller Booking Flow with Transparent Badges & Live Pricing */
          <TravellerPortal
            selectedDate={selectedDate}
            onBookingConfirmed={handleEventEmitted}
            locale={locale}
            t={t}
          />

        ) : (
          /* Admin Dynamic Pricing Control Plane Dashboard */
          <>
            {/* KPI Metrics Row */}
            <MetricsRow
              floorPrice={currentEntityMeta?.floor_price || 2485.41}
              ceilingPrice={currentEntityMeta?.ceiling_price || 6130.68}
              maxDailyMovePct={currentEntityMeta?.max_daily_move_pct || 0.15}
              effectivePrice={pricingData.effective_price}
              basePrice={pricingData.base_price}
              boundClamped={pricingData.bound_clamped}
              t={t}
            />

            {/* 30-Day Dual Axis Forecast Chart with Guardrail Clamp Report */}
            <ForecastChart
              forecastData={forecastCurve}
              showSimulation={hasSimulated}
              floorPrice={currentEntityMeta?.floor_price || 2485.41}
              ceilingPrice={currentEntityMeta?.ceiling_price || 6130.68}
              basePrice={pricingData.base_price || 3697.89}
              onInspectPoint={handleInspectPoint}
              onOpenOverrideModal={() => handleOpenOverride({ date: selectedDate })}
              t={t}
            />

            {/* Middle Split Grid: Explainability & What-If Simulator */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Factor Decomposition & Multilingual Audit */}
              <ExplainabilityCard
                explainData={explainData}
                selectedDate={selectedDate}
                locale={locale}
                t={t}
              />

              {/* What-If Scenario Simulator */}
              <SimulatorCard
                baseMultiplier={baseMultiplier}
                setBaseMultiplier={setBaseMultiplier}
                dailyMoveLimit={dailyMoveLimit}
                setDailyMoveLimit={setDailyMoveLimit}
                onRunSimulation={handleRunSimulation}
                simulationResults={simulationResults}
                isSimulating={isSimulating}
                onResetSimulation={handleResetSimulation}
                t={t}
              />
            </div>

            {/* Live Telemetry & Audit Activity Stream */}
            <RecentEventsLog
              events={recentEvents}
              onOpenEventModal={() => setIsEventModalOpen(true)}
              t={t}
            />
          </>
        )}
      </main>

      {/* Guardrail Clamp Inspector Modal */}
      <ClampInspectorModal
        isOpen={isClampInspectorOpen}
        onClose={() => setIsClampInspectorOpen(false)}
        pointData={inspectedPointData}
        entityName={currentEntityMeta?.entity_name || 'Selected Entity'}
        locale={locale}
        onOpenOverride={(pt) => handleOpenOverride(pt)}
      />

      {/* Admin Manual Price Override Modal */}
      <ManualOverrideModal
        isOpen={isOverrideModalOpen}
        onClose={() => setIsOverrideModalOpen(false)}
        selectedEntity={selectedEntity}
        entityName={currentEntityMeta?.entity_name || 'Selected Entity'}
        defaultDate={overrideDateTarget}
        floorPrice={currentEntityMeta?.floor_price || 2485.41}
        ceilingPrice={currentEntityMeta?.ceiling_price || 6130.68}
        currentPrice={pricingData.effective_price}
        onOverrideApplied={handleOverrideApplied}
      />

      {/* Telemetry Event Ingestion Modal */}
      <EventModal
        isOpen={isEventModalOpen}
        onClose={() => setIsEventModalOpen(false)}
        entityId={selectedEntity}
        selectedDate={selectedDate}
        onEventEmitted={handleEventEmitted}
      />

      {/* Hierarchical ML Model Performance Diagnostics Modal */}
      <ModelDiagnosticsModal
        isOpen={isModelDiagnosticsOpen}
        onClose={() => setIsModelDiagnosticsOpen(false)}
        metrics={forecasterMetrics}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-4 text-center text-xs text-slate-500">
        &copy; 2026 JETT 2 HOLIDAY &bull; Real-Time Dynamic Pricing &amp; Demand Forecasting (APS-02)
      </footer>
    </div>
  );
}

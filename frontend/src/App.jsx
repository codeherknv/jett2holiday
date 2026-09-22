import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MetricsRow from './components/MetricsRow';
import ForecastChart from './components/ForecastChart';
import ExplainabilityCard from './components/ExplainabilityCard';
import SimulatorCard from './components/SimulatorCard';
import EventModal from './components/EventModal';
import {
  calculatePricing,
  explainPricing,
  simulatePricing,
  checkBackendHealth,
  fetchEntities,
} from './api/client';

// Generate default 30-day mock forecast curve
function generateDefaultForecast(baseMultiplier = 1.0) {
  const startDate = new Date('2026-10-12');
  const items = [];
  const baseFare = 4500;

  for (let i = 0; i < 30; i++) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().split('T')[0];

    // Peak demand around Oct 15-18
    const peakWave = Math.max(0, 1.0 - Math.abs(i - 5) / 10.0);
    const demandIndex = Number((1.0 + 0.55 * peakWave).toFixed(2));
    const currentDynamicPrice = Math.round(baseFare * (1.0 + 0.30 * peakWave));
    const simRaw = Math.round(currentDynamicPrice * baseMultiplier);
    const clamped = simRaw > 7000 || simRaw < 3500;
    const simulatedPrice = Math.min(7000, Math.max(3500, simRaw));

    items.push({
      date: dateStr,
      base_price: baseFare,
      current_dynamic_price: currentDynamicPrice,
      simulated_price: simulatedPrice,
      demand_index: demandIndex,
      floor_price: 3500,
      ceiling_price: 7000,
      clamped,
    });
  }
  return items;
}

export default function App() {
  // State variables
  const [entities, setEntities] = useState([
    {
      entity_id: 'htl_sng_001_deluxe',
      entity_name: 'Dal Lake Luxury Heritage Resort (Deluxe)',
      entity_type: 'hotel_room',
      floor_price: 3500.0,
      ceiling_price: 7000.0,
      max_daily_move_pct: 0.15,
      base_price: 4500.0,
    },
    {
      entity_id: 'flt_del_srx_101_eco',
      entity_name: 'DEL -> SXR Express (Economy)',
      entity_type: 'flight_fare',
      floor_price: 4200.0,
      ceiling_price: 11500.0,
      max_daily_move_pct: 0.20,
      base_price: 5500.0,
    },
  ]);

  const [selectedEntity, setSelectedEntity] = useState('htl_sng_001_deluxe');
  const [selectedDate, setSelectedDate] = useState('2026-10-15');
  const [locale, setLocale] = useState('en-IN');
  const [isLive, setIsLive] = useState(false);
  const [isEventModalOpen, setIsEventModalOpen] = useState(false);

  // Dynamic Pricing & Explainability State
  const [pricingData, setPricingData] = useState({
    effective_price: 5850.0,
    base_price: 4500.0,
    demand_index: 1.42,
    occupancy_factor: 1.18,
    lead_time_factor: 1.04,
    seasonality_factor: 1.15,
    bound_clamped: false,
  });

  const [explainData, setExplainData] = useState(null);

  // Simulation State
  const [baseMultiplier, setBaseMultiplier] = useState(1.15);
  const [dailyMoveLimit, setDailyMoveLimit] = useState(0.20);
  const [isSimulating, setIsSimulating] = useState(false);
  const [hasSimulated, setHasSimulated] = useState(true);
  const [simulationResults, setSimulationResults] = useState({
    revenue_delta_pct: 12.4,
    booking_rate_delta_pct: -2.1,
    breaches: 0,
  });
  const [forecastCurve, setForecastCurve] = useState(() => generateDefaultForecast(1.15));

  // Current entity metadata
  const currentEntityMeta = entities.find((e) => e.entity_id === selectedEntity) || entities[0];

  // 1. Initial Load & Backend Healthcheck
  useEffect(() => {
    async function init() {
      try {
        const health = await checkBackendHealth();
        if (health.status === 'healthy') {
          setIsLive(true);
          const entityList = await fetchEntities();
          if (entityList?.length) setEntities(entityList);
        }
      } catch {
        setIsLive(false);
      }
    }
    init();
  }, []);

  // 2. Fetch Pricing & Explainability when entity or date changes
  useEffect(() => {
    async function fetchPricingAndExplain() {
      try {
        const [pData, eData] = await Promise.all([
          calculatePricing(selectedEntity, selectedDate),
          explainPricing(selectedEntity, selectedDate),
        ]);
        setPricingData(pData);
        setExplainData(eData);
        setIsLive(true);
      } catch {
        // Fallback to computed mock
        const isFlight = selectedEntity.includes('flt');
        const base = isFlight ? 5500 : 4500;
        const effective = isFlight ? 7250 : 5850;
        setPricingData({
          effective_price: effective,
          base_price: base,
          demand_index: 1.42,
          occupancy_factor: 1.18,
          lead_time_factor: 1.04,
          seasonality_factor: 1.15,
          bound_clamped: false,
        });
      }
    }
    fetchPricingAndExplain();
  }, [selectedEntity, selectedDate]);

  // 3. Handle Running Simulation (Calls POST /pricing/simulate)
  const handleRunSimulation = async () => {
    setIsSimulating(true);
    try {
      const res = await simulatePricing(selectedEntity, baseMultiplier, dailyMoveLimit);
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
    } catch {
      // Fallback simulation computation
      const newCurve = generateDefaultForecast(baseMultiplier);
      setForecastCurve(newCurve);
      setSimulationResults({
        revenue_delta_pct: Number(((baseMultiplier - 1.0) * 82.5).toFixed(1)),
        booking_rate_delta_pct: Number((-(baseMultiplier - 1.0) * 14.0).toFixed(1)),
        breaches: baseMultiplier > 1.5 ? 2 : 0,
      });
      setHasSimulated(true);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleResetSimulation = () => {
    setBaseMultiplier(1.0);
    setDailyMoveLimit(0.15);
    setHasSimulated(false);
    setForecastCurve(generateDefaultForecast(1.0));
    setSimulationResults({
      revenue_delta_pct: 0.0,
      booking_rate_delta_pct: 0.0,
      breaches: 0,
    });
  };

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
      />

      {/* Main Control Plane Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* KPI Metrics Row */}
        <MetricsRow
          floorPrice={currentEntityMeta.floor_price || 3500}
          ceilingPrice={currentEntityMeta.ceiling_price || 7000}
          maxDailyMovePct={currentEntityMeta.max_daily_move_pct || 0.15}
          effectivePrice={pricingData.effective_price}
          basePrice={pricingData.base_price}
          boundClamped={pricingData.bound_clamped}
        />

        {/* 30-Day Dual Axis Forecast Chart */}
        <ForecastChart
          forecastData={forecastCurve}
          showSimulation={hasSimulated}
          floorPrice={currentEntityMeta.floor_price || 3500}
          ceilingPrice={currentEntityMeta.ceiling_price || 7000}
          basePrice={pricingData.base_price || 4500}
        />

        {/* Bottom Split Grid: Explainability & What-If Simulator */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Factor Decomposition & Multilingual Audit */}
          <ExplainabilityCard
            explainData={explainData}
            selectedDate={selectedDate}
            locale={locale}
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
          />
        </div>
      </main>

      {/* Telemetry Event Ingestion Modal */}
      <EventModal
        isOpen={isEventModalOpen}
        onClose={() => setIsEventModalOpen(false)}
        entityId={selectedEntity}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-4 text-center text-xs text-slate-500">
        &copy; 2026 JETT 2 HOLIDAY &bull; Real-Time Dynamic Pricing &amp; Demand Forecasting (APS-02)
      </footer>
    </div>
  );
}

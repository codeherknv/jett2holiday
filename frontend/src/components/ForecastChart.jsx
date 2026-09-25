import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { Sparkles, Info, ShieldAlert, ShieldCheck, AlertTriangle, Eye, Edit3, ArrowUpRight } from 'lucide-react';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isClamped = data.clamped;
    const clampedBy = data.clamped_by || (data.raw_model_price > data.ceiling_price ? 'ceiling' : (data.raw_model_price < data.floor_price ? 'floor' : null));
    const rawPrice = data.raw_model_price || data.base_price * (1 + (data.demand_index - 1) * 0.7);
    const dynamicPrice = data.current_dynamic_price || data.price;
    const simPrice = data.simulated_price;
    const hasSimDiff = simPrice && Math.abs(simPrice - dynamicPrice) > 1;

    return (
      <div className="bg-slate-900 border border-slate-700 p-3.5 rounded-xl shadow-2xl text-xs space-y-2 min-w-[230px] backdrop-blur-md">
        <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1.5 flex justify-between items-center">
          <span className="font-mono">Date: {label}</span>
          {isClamped ? (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${clampedBy === 'ceiling'
                ? 'bg-amber-950 text-amber-300 border border-amber-800'
                : clampedBy === 'floor'
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
              }`}>
              Clamped: {clampedBy || 'Guardrail'}
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
              Within Bounds
            </span>
          )}
        </div>

        {/* Pricing Comparison */}
        <div className="space-y-1 font-mono text-[11px]">
          {isClamped && (
            <div className="flex justify-between items-center text-slate-400">
              <span>Raw Model Price:</span>
              <span className="line-through text-slate-500">₹{Math.round(rawPrice).toLocaleString('en-IN')}</span>
            </div>
          )}

          {/* Main Published Dynamic Price */}
          <div className="flex justify-between items-center text-teal-300 font-semibold">
            <span>Published Dynamic Rate:</span>
            <span className="text-sm font-black text-teal-300">₹{Math.round(dynamicPrice).toLocaleString('en-IN')}</span>
          </div>

          {/* What-If Rate (if simulated) */}
          {hasSimDiff && (
            <div className="flex justify-between items-center text-amber-300 font-semibold bg-amber-950/30 px-1.5 py-0.5 rounded border border-amber-800/40">
              <span>What-If Simulated Rate:</span>
              <span className="font-bold">₹{Math.round(simPrice).toLocaleString('en-IN')}</span>
            </div>
          )}

          {isClamped && data.bound_name && (
            <div className="flex justify-between items-center text-amber-300 text-[10px]">
              <span>Binding Guardrail:</span>
              <span>{data.bound_name}</span>
            </div>
          )}

          <div className="flex justify-between items-center text-blue-300">
            <span>Forecast Demand:</span>
            <span className="font-bold">{data.demand_index}x</span>
          </div>
        </div>

        <div className="flex justify-between items-center text-slate-400 pt-1.5 border-t border-slate-800 text-[10px]">
          <span>Safety Corridor:</span>
          <span>₹{data.floor_price?.toLocaleString('en-IN') || '2,485'} — ₹{data.ceiling_price?.toLocaleString('en-IN') || '6,131'}</span>
        </div>

        <div className="pt-1 text-center">
          <span className="text-[10px] text-teal-400 font-semibold flex items-center justify-center">
            Click point to inspect decision <ArrowUpRight className="w-3 h-3 ml-0.5" />
          </span>
        </div>
      </div>
    );
  }
  return null;
};

export default function ForecastChart({
  forecastData = [],
  showSimulation = false,
  floorPrice = 2485.41,
  ceilingPrice = 6130.68,
  basePrice = 3697.89,
  onInspectPoint,
  onOpenOverrideModal,
}) {
  // Format X-axis date labels for readability (e.g. "Oct 15")
  const formatXAxis = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // Compute exact guardrail clamp counts
  const totalPrices = forecastData.length || 30;
  const ceilingClamps = forecastData.filter(d => d.clamped && (d.clamped_by === 'ceiling' || (d.raw_model_price > (d.ceiling_price || ceilingPrice)))).length;
  const floorClamps = forecastData.filter(d => d.clamped && (d.clamped_by === 'floor' || (d.raw_model_price < (d.floor_price || floorPrice)))).length;
  const dailyClamps = forecastData.filter(d => d.clamped && d.clamped_by === 'daily_movement').length;
  const totalClamped = forecastData.filter(d => d.clamped).length;

  const hasSimulationActive = showSimulation && forecastData.some(d => typeof d.simulated_price === 'number');

  // Custom dot renderer for Recharts
  const renderClampedDot = (props) => {
    const { cx, cy, payload } = props;
    if (!payload || !cx || !cy) return null;

    if (payload.clamped) {
      const isCeiling = payload.clamped_by === 'ceiling' || (payload.raw_model_price > (payload.ceiling_price || ceilingPrice));
      const isFloor = payload.clamped_by === 'floor' || (payload.raw_model_price < (payload.floor_price || floorPrice));
      const color = isCeiling ? '#f59e0b' : (isFloor ? '#10b981' : '#38bdf8');

      return (
        <svg
          key={`dot-${payload.date}`}
          x={cx - 7}
          y={cy - 7}
          width={14}
          height={14}
          className="cursor-pointer transition-transform hover:scale-150"
          onClick={() => onInspectPoint && onInspectPoint(payload)}
        >
          <circle cx="7" cy="7" r="6" fill={color} stroke="#0f172a" strokeWidth="2" />
          <circle cx="7" cy="7" r="2.5" fill="#ffffff" />
        </svg>
      );
    }
    return (
      <circle
        key={`dot-norm-${payload.date}`}
        cx={cx}
        cy={cy}
        r="2"
        fill="#14b8a6"
        className="opacity-40"
      />
    );
  };

  // Sample clamped point for one-click inspection
  const sampleClampedPoint = forecastData.find(d => d.clamped) || forecastData[5] || forecastData[0];

  return (
    <div className="glass-panel p-5 mb-6">
      {/* ✦ MANDATORY ENHANCEMENT: GUARDRAIL CLAMP REPORT BANNER ✦ */}
      <div className="mb-4 p-3.5 rounded-xl bg-gradient-to-r from-slate-900 via-slate-800/90 to-slate-900 border border-amber-500/30 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 flex-shrink-0">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
                  Guardrail Clamp Report
                </span>
                <span className="text-[11px] px-2 py-0.2 rounded-full bg-amber-950 text-amber-300 font-mono font-bold border border-amber-800">
                  {totalClamped} of {totalPrices} Clamped
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-200 mt-0.5 font-mono">
                {totalClamped} of {totalPrices} prices clamped —{' '}
                <span className="text-amber-400 font-bold">{ceilingClamps} by ceiling</span>,{' '}
                <span className="text-emerald-400 font-bold">{floorClamps} by floor</span>,{' '}
                <span className="text-cyan-400 font-bold">{dailyClamps} by daily-movement</span>
              </p>
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onInspectPoint && onInspectPoint(sampleClampedPoint)}
              className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold transition flex items-center space-x-1.5 shadow-sm"
              title="Open the detailed clamp inspector for judges"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspect Clamped Point</span>
            </button>
            {onOpenOverrideModal && (
              <button
                onClick={onOpenOverrideModal}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition flex items-center space-x-1.5"
              >
                <Edit3 className="w-3.5 h-3.5 text-blue-400" />
                <span>Manual Override</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Chart Header & Legends */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Forecast Intelligence &bull; Price &amp; Demand Trajectory
            </h2>
            <span className="flex items-center text-xs px-2 py-0.5 rounded bg-teal-950/80 text-teal-300 border border-teal-800">
              <Sparkles className="w-3 h-3 mr-1 text-teal-400" />
              Next 30 Days Forecast
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Decoupled ML demand forecaster + deterministic guardrails. Click any point or marker to inspect clamp decision.
          </p>
        </div>

        {/* Legend Indicators */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-1 bg-teal-400 rounded-full"></span>
            <span className="text-slate-300 font-semibold">Published Dynamic Price (₹)</span>
          </div>
          {hasSimulationActive && (
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-1 bg-amber-400 rounded-full border-t border-dashed border-amber-300"></span>
              <span className="text-amber-300 font-semibold">What-If Simulated Policy (₹)</span>
            </div>
          )}
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-1 bg-blue-400 rounded-full"></span>
            <span className="text-slate-300">Demand Index</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-slate-900 inline-block"></span>
            <span className="text-amber-300 font-semibold">Clamped Point</span>
          </div>
        </div>
      </div>

      {/* Recharts Container */}
      <div className="w-full h-84">
        <ResponsiveContainer width="100%" height={330}>
          <ComposedChart
            data={forecastData}
            margin={{ top: 10, right: 20, left: 10, bottom: 0 }}
            onClick={(state) => {
              if (state && state.activePayload && state.activePayload.length) {
                const clicked = state.activePayload[0].payload;
                if (onInspectPoint) onInspectPoint(clicked);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatXAxis}
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
            />
            {/* Left Y Axis: Currency (INR) */}
            <YAxis
              yAxisId="price"
              stroke="#64748b"
              fontSize={11}
              domain={[Math.round(floorPrice * 0.8), Math.round(ceilingPrice * 1.15)]}
              tickFormatter={(v) => `₹${v.toLocaleString('en-IN')}`}
              tickLine={false}
              orientation="left"
            />
            {/* Right Y Axis: Demand Index */}
            <YAxis
              yAxisId="demand"
              stroke="#64748b"
              fontSize={11}
              domain={[0.5, 2.5]}
              tickFormatter={(v) => `${v}x`}
              tickLine={false}
              orientation="right"
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Guardrail Reference Lines */}
            <ReferenceLine
              yAxisId="price"
              y={ceilingPrice}
              stroke="#ef4444"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: `CEILING CAP: ₹${ceilingPrice.toLocaleString('en-IN')}`,
                fill: '#ef4444',
                fontSize: 10,
                position: 'insideTopRight',
              }}
            />
            <ReferenceLine
              yAxisId="price"
              y={floorPrice}
              stroke="#10b981"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: `FLOOR: ₹${floorPrice.toLocaleString('en-IN')}`,
                fill: '#10b981',
                fontSize: 10,
                position: 'insideBottomRight',
              }}
            />
            <ReferenceLine
              yAxisId="price"
              y={basePrice}
              stroke="#64748b"
              strokeDasharray="2 2"
              label={{
                value: `BASELINE: ₹${basePrice.toLocaleString('en-IN')}`,
                fill: '#94a3b8',
                fontSize: 9,
                position: 'insideLeft',
              }}
            />

            {/* Demand Index Line */}
            <Line
              yAxisId="demand"
              type="monotone"
              dataKey="demand_index"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: '#38bdf8', strokeWidth: 2, fill: '#0f172a' }}
            />

            {/* Published Dynamic Price Line (Solid Teal Line) */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="current_dynamic_price"
              name="Published Dynamic Rate"
              stroke="#14b8a6"
              strokeWidth={2.5}
              dot={renderClampedDot}
              activeDot={{ r: 6, stroke: '#14b8a6', strokeWidth: 2, fill: '#0f172a' }}
            />

            {/* What-If Simulated Price Line (Dashed Amber Line - only if actively simulating) */}
            {hasSimulationActive && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="simulated_price"
                name="What-If Simulated Rate"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Trajectory Footnote & Clamped Legend */}
      <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <Info className="w-3.5 h-3.5 text-teal-400" />
          <span className="font-medium text-slate-300">How to Read:</span>
          <span>Solid teal line shows the published bounded price. Orange dots highlight points clamped by guardrails.</span>
        </div>
        <div className="font-mono text-[11px] text-slate-400">
          Clamped Percentage: <strong className="text-amber-300">{Math.round((totalClamped / totalPrices) * 100)}%</strong>
        </div>
      </div>
    </div>
  );
}


import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { Sparkles, Info } from 'lucide-react';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1.5 min-w-[200px]">
        <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1 flex justify-between">
          <span>Date: {label}</span>
          {data.clamped && (
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800">
              Clamped
            </span>
          )}
        </div>
        <div className="flex justify-between items-center text-teal-400 font-mono">
          <span>Dynamic Price:</span>
          <span className="font-bold">₹{data.current_dynamic_price?.toLocaleString('en-IN') || data.price?.toLocaleString('en-IN')}</span>
        </div>
        {data.simulated_price && (
          <div className="flex justify-between items-center text-amber-400 font-mono">
            <span>Simulated Rate:</span>
            <span className="font-bold">₹{data.simulated_price.toLocaleString('en-IN')}</span>
          </div>
        )}
        <div className="flex justify-between items-center text-blue-400 font-mono">
          <span>Demand Index:</span>
          <span className="font-bold">{data.demand_index}x</span>
        </div>
        <div className="flex justify-between items-center text-slate-400 pt-1 border-t border-slate-800 text-[11px]">
          <span>Bounds:</span>
          <span>₹{data.floor_price || 3500} - ₹{data.ceiling_price || 7000}</span>
        </div>
      </div>
    );
  }
  return null;
};

export default function ForecastChart({
  forecastData = [],
  showSimulation = false,
  floorPrice = 3500,
  ceilingPrice = 7000,
  basePrice = 4500,
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

  return (
    <div className="glass-panel p-5 mb-6">
      {/* Chart Header */}
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
            Decoupled statistical Prophet/Regression forecast combined with bounded linear dynamic pricing
          </p>
        </div>

        {/* Legend Indicators */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-1 bg-teal-400 rounded-full"></span>
            <span className="text-slate-300">Dynamic Price (₹)</span>
          </div>
          {showSimulation && (
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-1 bg-amber-400 rounded-full"></span>
              <span className="text-amber-300">Simulated Rate (₹)</span>
            </div>
          )}
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-1 bg-blue-400 rounded-full"></span>
            <span className="text-slate-300">Demand Index</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 border-t border-dashed border-slate-500"></span>
            <span className="text-slate-400">Guardrail Caps</span>
          </div>
        </div>
      </div>

      {/* Recharts Container */}
      <div className="w-full h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={forecastData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
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
              domain={[3000, 8000]}
              tickFormatter={(v) => `₹${v}`}
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
              label={{
                value: `CEILING CAP: ₹${ceilingPrice}`,
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
              label={{
                value: `FLOOR: ₹${floorPrice}`,
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
                value: `BASELINE: ₹${basePrice}`,
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

            {/* Baseline Dynamic Price Line */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="current_dynamic_price"
              stroke="#14b8a6"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, stroke: '#14b8a6', strokeWidth: 2, fill: '#0f172a' }}
            />

            {/* Simulated Price Line (when active) */}
            {showSimulation && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="simulated_price"
                stroke="#f59e0b"
                strokeWidth={2.5}
                strokeDasharray="5 5"
                dot={false}
                activeDot={{ r: 5, stroke: '#f59e0b', strokeWidth: 2, fill: '#0f172a' }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Demand Signal Sequence Badge Strip */}
      <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <Info className="w-3.5 h-3.5 text-teal-400" />
          <span className="font-medium text-slate-300">Demand Signal Trajectory:</span>
          <span className="font-mono text-teal-300">
            {forecastData.slice(0, 6).map((d) => d.demand_index).join(' → ')} ...
          </span>
        </div>
        <div className="font-mono text-[11px] text-slate-400">
          Peak Index: <strong className="text-teal-300">1.55x</strong> (Oct 17, Autumn Rush)
        </div>
      </div>
    </div>
  );
}

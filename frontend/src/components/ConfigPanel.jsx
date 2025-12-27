import React, { useState } from 'react'
import { Settings, Users, Play, BarChart, TrendingUp, Zap } from 'lucide-react'

const ConfigPanel = ({ setResults, setLoading, results, activeRoute, setActiveRoute }) => {
    const [instance, setInstance] = useState('data/c102.txt')
    const [customers, setCustomers] = useState(100)

    const handleSolve = async () => {
        setLoading(true)
        setResults(null)
        setActiveRoute(null)

        try {
            const response = await fetch('/api/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instance_file: instance, max_customers: Number(customers) })
            })
            const data = await response.json()
            if (data.success) {
                setResults(data)
            } else {
                alert(`Error: ${data.error}`)
            }
        } catch (error) {
            alert(`Failed to solve: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="glass-card p-8 flex flex-col gap-6">
                <div className="flex justify-between items-center border-b border-border pb-4">
                    <h2 className="font-outfit text-xl font-bold flex items-center gap-2">
                        <Settings size={20} className="text-primary-light" /> Configuration
                    </h2>
                    <span className="text-[10px] font-bold bg-primary/20 text-primary-light px-2 py-1 rounded border border-primary/30 uppercase">v1.0</span>
                </div>

                <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                        <BarChart size={14} /> Problem Instance
                    </label>
                    <div className="relative group">
                        <select
                            value={instance}
                            onChange={(e) => setInstance(e.target.value)}
                            className="w-full bg-dark-bg/60 border border-border rounded-xl px-4 py-3.5 text-sm font-medium focus:outline-none focus:border-primary-light hover:bg-dark-bg/80 transition-all cursor-pointer appearance-none"
                        >
                            <option value="data/c102.txt">C102 - Clustered Layout</option>
                            <option value="data/c101.txt">C101 - Clustered Layout</option>
                            <option value="data/r101.txt">R101 - Random Distribution</option>
                            <option value="data/rc101.txt">RC101 - Mixed Pattern</option>
                        </select>
                    </div>
                </div>

                <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                        <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                            <Users size={14} /> Customers
                        </label>
                        <span className="text-xs font-bold text-primary-light bg-primary/10 px-2.5 py-1 rounded-lg">{customers}</span>
                    </div>
                    <input
                        type="range"
                        min="25"
                        max="100"
                        step="25"
                        value={customers}
                        onChange={(e) => setCustomers(e.target.value)}
                        className="w-full h-1.5 bg-gradient-to-r from-primary to-secondary rounded-lg appearance-none cursor-pointer accent-primary-light"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted font-bold px-1">
                        <span>25</span><span>50</span><span>75</span><span>100</span>
                    </div>
                </div>

                <button
                    onClick={handleSolve}
                    className="w-full py-4 bg-gradient-to-r from-primary to-primary-light rounded-xl font-outfit font-bold text-white flex items-center justify-center gap-3 shadow-xl shadow-primary/30 hover:-translate-y-1 hover:shadow-primary/50 transition-all active:translate-y-0"
                >
                    <Play size={20} fill="currentColor" /> Solve Route
                </button>

                {results && (
                    <div className="mt-4 pt-6 border-t border-border flex flex-col gap-6 animate-in fade-in slide-in-from-top-4 duration-500">
                        <h3 className="font-outfit text-sm font-bold text-text-primary uppercase tracking-tight">Solution Results</h3>

                        <div className="grid grid-cols-2 gap-3">
                            <StatCard label="Total Cost" value={results.total_cost.toFixed(2)} color="primary" />
                            <StatCard label="Vehicles" value={results.num_vehicles} color="secondary" />
                            <StatCard label="Solve Time" value={`${results.solve_time}s`} color="success" />
                            <div className={`p-4 bg-dark-bg/80 border rounded-xl flex flex-col items-center justify-center gap-1 ${results.feasible ? 'border-success/30' : 'border-danger/30'}`}>
                                <span className={`text-[10px] font-bold uppercase rounded-md px-2 py-0.5 ${results.feasible ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                                    {results.feasible ? 'Feasible' : 'Infeasible'}
                                </span>
                                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Status</span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Route Details</h4>
                            <div className="flex flex-col gap-2 max-height-280 overflow-y-auto pr-1">
                                {results.routes.map((route, idx) => (
                                    <button
                                        key={route.route_id}
                                        onClick={() => setActiveRoute(activeRoute === idx ? null : idx)}
                                        className={`flex justify-between items-center p-3.5 bg-dark-bg/80 border rounded-xl text-left transition-all hover:translate-x-1 ${activeRoute === idx ? 'border-primary-light bg-primary/10' : 'border-border'}`}
                                    >
                                        <div>
                                            <div className="text-sm font-bold">Route {route.route_id}</div>
                                            <div className="text-[10px] text-text-muted font-medium">{route.num_customers} stops • Load: {route.load}</div>
                                        </div>
                                        <div className="text-sm font-black text-primary-light">${route.cost.toFixed(2)}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

const StatCard = ({ label, value, color }) => {
    const colorMap = {
        primary: 'border-primary/40 text-primary-light bg-primary/5',
        secondary: 'border-secondary/40 text-secondary-light bg-secondary/5',
        success: 'border-success/40 text-success bg-success/5',
    }
    return (
        <div className={`p-4 border rounded-xl flex flex-col items-center justify-center transition-transform hover:-translate-y-1 ${colorMap[color]}`}>
            <span className="font-outfit text-xl font-black text-text-primary">{value}</span>
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">{label}</span>
        </div>
    )
}

export default ConfigPanel

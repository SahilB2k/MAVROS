import React, { useState } from 'react'
import Header from './components/Header'
import ConfigPanel from './components/ConfigPanel'
import VisualizationPanel from './components/VisualizationPanel'
import ComparisonView from './components/ComparisonView'

function App() {
    const [view, setView] = useState('dashboard')
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)
    const [activeRoute, setActiveRoute] = useState(null)

    return (
        <div className="min-h-screen bg-dark-bg text-slate-200">
            <div className="bg-animation">
                <div className="gradient-orb orb-1"></div>
                <div className="gradient-orb orb-2"></div>
                <div className="grid-lines"></div>
            </div>

            <Header view={view} setView={setView} />

            <main className="max-w-[1600px] mx-auto px-6 py-10 relative z-10">
                {view === 'dashboard' ? (
                    <div className="grid grid-cols-1 xl:grid-cols-[400px_1fr] gap-10">
                        <div className="flex flex-col gap-6">
                            <ConfigPanel
                                setResults={setResults}
                                setLoading={setLoading}
                                results={results}
                                activeRoute={activeRoute}
                                setActiveRoute={setActiveRoute}
                            />
                        </div>
                        <div className="flex flex-col gap-6">
                            <VisualizationPanel
                                results={results}
                                loading={loading}
                                activeRoute={activeRoute}
                                setActiveRoute={setActiveRoute}
                            />
                        </div>
                    </div>
                ) : (
                    <ComparisonView results={results} />
                )}
            </main>

            <footer className="py-10 text-center text-slate-500 text-sm relative z-10 border-t border-white/5 mt-10 bg-dark-bg/50 backdrop-blur-md">
                <div className="max-w-7xl mx-auto px-6">
                    <p>© 2025 MAVROS • Advanced AI Route Optimization Engine</p>
                    <p className="text-[10px] uppercase tracking-widest mt-2 opacity-40 italic">Experimental High-Efficiency Solver v1.0.4</p>
                </div>
            </footer>
        </div>
    )
}

export default App

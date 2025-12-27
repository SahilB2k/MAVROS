import React from 'react'
import { ShieldCheck, BarChart3, LayoutDashboard, Cpu } from 'lucide-react'

const Header = ({ view, setView }) => {
    return (
        <header className="sticky top-0 z-50 bg-dark-bg/70 backdrop-blur-xl border-b border-border py-4">
            <div className="container flex justify-between items-center">
                <div className="flex items-center gap-4 cursor-pointer" onClick={() => setView('dashboard')}>
                    <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20 hover:-translate-y-0.5 transition-transform">
                        <ShieldCheck className="text-white" size={26} />
                    </div>
                    <div>
                        <h1 className="font-outfit text-2xl font-extrabold bg-gradient-to-r from-primary-light to-secondary-light bg-clip-text text-transparent tracking-tight">
                            MAVROS
                        </h1>
                        <p className="text-[10px] text-text-muted font-semibold uppercase tracking-wider">
                            Intelligent Route Optimization
                        </p>
                    </div>
                </div>

                <nav className="flex items-center gap-8">
                    <button
                        onClick={() => setView('dashboard')}
                        className={`flex items-center gap-2 text-sm font-medium transition-colors ${view === 'dashboard' ? 'text-primary-light' : 'text-text-secondary hover:text-primary-light'}`}
                    >
                        <LayoutDashboard size={16} /> Dashboard
                    </button>
                    <button
                        onClick={() => setView('comparison')}
                        className={`flex items-center gap-2 text-sm font-medium transition-colors ${view === 'comparison' ? 'text-primary-light' : 'text-text-secondary hover:text-primary-light'}`}
                    >
                        <BarChart3 size={16} /> Performance
                    </button>
                    <a href="#" className="hidden md:flex items-center gap-2 text-sm font-medium text-text-secondary hover:text-primary-light transition-colors">
                        <Cpu size={16} /> API
                    </a>
                    <button className="px-6 py-2 border border-border rounded-lg text-sm font-semibold text-text-secondary hover:border-primary-light hover:text-primary-light hover:bg-primary/5 transition-all">
                        Learn More
                    </button>
                </nav>
            </div>
        </header>
    )
}

export default Header

import React, { useRef, useEffect, useState } from 'react'
import { Maximize2, Download, RotateCcw } from 'lucide-react'

const ROUTE_COLORS = [
    "#6366F1", "#06B6D4", "#F97316", "#10B981", "#8B5CF6",
    "#EC4899", "#F59E0B", "#14B8A6", "#3B82F6", "#A855F7",
    "#D946EF", "#0EA5E9", "#84CC16", "#06B6D4", "#4F46E5",
]

const VisualizationPanel = ({ results, loading, activeRoute, setActiveRoute }) => {
    const canvasRef = useRef(null)
    const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, content: null })

    useEffect(() => {
        if (!results) return
        draw(results)

        const handleResize = () => draw(results)
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [results, activeRoute])

    const draw = (data) => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')

        // Handle high DPI
        const dpr = window.devicePixelRatio || 1
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * dpr
        canvas.height = rect.height * dpr
        ctx.scale(dpr, dpr)

        const width = rect.width
        const height = rect.height

        const allPoints = [data.depot, ...data.customers]
        const xCoords = allPoints.map((p) => p.x)
        const yCoords = allPoints.map((p) => p.y)
        const minX = Math.min(...xCoords)
        const maxX = Math.max(...xCoords)
        const minY = Math.min(...yCoords)
        const maxY = Math.max(...yCoords)

        const padding = 60
        const scaleX = (width - 2 * padding) / (maxX - minX || 1)
        const scaleY = (height - 2 * padding) / (maxY - minY || 1)
        const scale = Math.min(scaleX, scaleY)

        const transform = (x, y) => ({
            x: padding + (x - minX) * scale,
            y: height - (padding + (y - minY) * scale),
        })

        ctx.clearRect(0, 0, width, height)

        // 1. Draw inactive (dimmed) routes
        data.routes.forEach((route, index) => {
            if (activeRoute !== null && activeRoute !== index) {
                drawRoute(ctx, route, index, data, transform, true)
            }
        })

        // 2. Draw active (or all) routes
        data.routes.forEach((route, index) => {
            if (activeRoute === null || activeRoute === index) {
                drawRoute(ctx, route, index, data, transform, false)
            }
        })

        // 3. Draw Depot
        const depotPos = transform(data.depot.x, data.depot.y)
        ctx.shadowBlur = 10
        ctx.shadowColor = 'rgba(239, 68, 68, 0.4)'
        ctx.fillStyle = "#EF4444"
        ctx.beginPath()
        ctx.arc(depotPos.x, depotPos.y, 11, 0, 2 * Math.PI)
        ctx.fill()
        ctx.strokeStyle = "#FFF"
        ctx.lineWidth = 2.5
        ctx.stroke()
        ctx.shadowBlur = 0
        ctx.fillStyle = "#F1F5F9"
        ctx.font = "bold 13px Outfit"
        ctx.fillText("DEPOT", depotPos.x + 18, depotPos.y + 4)
    }

    const drawRoute = (ctx, route, index, data, transform, dimmed) => {
        const color = ROUTE_COLORS[index % ROUTE_COLORS.length]
        ctx.globalAlpha = dimmed ? 0.12 : 1.0
        ctx.strokeStyle = color
        ctx.lineWidth = (!dimmed && activeRoute === index) ? 4 : 2.5

        const depotPos = transform(data.depot.x, data.depot.y)
        ctx.beginPath()
        ctx.moveTo(depotPos.x, depotPos.y)

        route.customers.forEach((customer) => {
            const pos = transform(customer.x, customer.y)
            ctx.lineTo(pos.x, pos.y)
        })

        ctx.lineTo(depotPos.x, depotPos.y)
        ctx.stroke()

        // Draw nodes
        route.customers.forEach((customer) => {
            const pos = transform(customer.x, customer.y)
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(pos.x, pos.y, dimmed ? 4 : 5, 0, 2 * Math.PI)
            ctx.fill()
            if (!dimmed) {
                ctx.strokeStyle = "#0f172a"
                ctx.lineWidth = 1.5
                ctx.stroke()

                if (activeRoute === index) {
                    ctx.fillStyle = "#F1F5F9"
                    ctx.font = "bold 10px Inter"
                    ctx.textAlign = "center"
                    ctx.fillText(customer.id, pos.x, pos.y - 12)
                }
            }
        })
        ctx.globalAlpha = 1.0
    }

    const handleMouseMove = (e) => {
        if (!results) return
        const rect = canvasRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top

        // Simple point/segment hover detection (simplified for React)
        // Find closest node
        let closestCustomer = null
        let minDist = 15

        const xCoords = [results.depot.x, ...results.customers.map(c => c.x)]
        const yCoords = [results.depot.y, ...results.customers.map(c => c.y)]
        const minX = Math.min(...xCoords)
        const maxX = Math.max(...xCoords)
        const minY = Math.min(...yCoords)
        const maxY = Math.max(...yCoords)
        const padding = 60
        const scaleX = (rect.width - 2 * padding) / (maxX - minX || 1)
        const scaleY = (rect.height - 2 * padding) / (maxY - minY || 1)
        const scale = Math.min(scaleX, scaleY)
        const transform = (px, py) => ({
            x: padding + (px - minX) * scale,
            y: rect.height - (padding + (py - minY) * scale),
        })

        results.customers.forEach(c => {
            const pos = transform(c.x, c.y)
            const d = Math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2)
            if (d < minDist) {
                minDist = d
                closestCustomer = c
            }
        })

        if (closestCustomer) {
            setTooltip({
                visible: true,
                x: e.clientX,
                y: e.clientY,
                content: (
                    <div className="bg-dark-card border border-border p-3 rounded-xl shadow-2xl backdrop-blur-md">
                        <div className="text-xs font-bold text-primary-light uppercase tracking-widest mb-1">Stall {closestCustomer.id}</div>
                        <div className="text-[10px] text-text-muted">Demand: <span className="text-text-primary font-bold">{closestCustomer.demand}</span></div>
                        <div className="text-[10px] text-text-muted">Window: <span className="text-text-primary font-bold">{closestCustomer.ready_time} - {closestCustomer.due_date}</span></div>
                    </div>
                )
            })
        } else {
            setTooltip({ ...tooltip, visible: false })
        }
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="glass-card p-6 min-h-[720px] relative flex flex-col">
                <div className="flex justify-between items-center border-b border-border pb-4 mb-4">
                    <h2 className="font-outfit text-xl font-bold">Route Visualization</h2>
                    <div className="flex gap-2">
                        <button className="p-2 bg-dark-bg/60 border border-border rounded-lg hover:text-primary-light transition-colors"><RotateCcw size={16} /></button>
                        <button className="p-2 bg-dark-bg/60 border border-border rounded-lg hover:text-primary-light transition-colors"><Download size={16} /></button>
                    </div>
                </div>

                <div className="relative flex-1 bg-dark-bg/40 rounded-2xl border border-border overflow-hidden">
                    {loading && (
                        <div className="absolute inset-0 bg-dark-bg/90 z-20 flex flex-col items-center justify-center gap-6">
                            <div className="relative w-24 h-24">
                                <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                                <div className="absolute inset-0 border-4 border-t-primary rounded-full animate-spin"></div>
                                <div className="absolute inset-4 border-4 border-t-secondary rounded-full animate-spin-slow"></div>
                            </div>
                            <div className="flex flex-col items-center">
                                <span className="font-outfit font-bold text-lg animate-pulse tracking-wider">Optimizing Route</span>
                                <span className="text-[10px] text-text-muted font-bold uppercase tracking-widest mt-1">Applying MDS Heuristics...</span>
                            </div>
                        </div>
                    )}

                    <canvas
                        ref={canvasRef}
                        className="w-full h-full cursor-crosshair"
                        onMouseMove={handleMouseMove}
                        onMouseLeave={() => setTooltip({ ...tooltip, visible: false })}
                    />

                    {!loading && results && (
                        <div className="absolute bottom-4 left-4 bg-dark-card/60 backdrop-blur-md border border-border rounded-xl p-3 flex flex-wrap gap-4 z-10 animate-in fade-in slide-in-from-bottom-2">
                            {results.routes.map((r, i) => (
                                <button
                                    key={i}
                                    onMouseEnter={() => activeRoute === null && setActiveRoute(i)}
                                    onMouseLeave={() => activeRoute === i && setActiveRoute(null)}
                                    className="flex items-center gap-2"
                                >
                                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ROUTE_COLORS[i % ROUTE_COLORS.length] }}></div>
                                    <span className="text-[10px] font-bold text-text-secondary">R{r.route_id}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {tooltip.visible && (
                    <div
                        className="fixed pointer-events-none z-50 transition-all duration-75"
                        style={{ left: tooltip.x + 15, top: tooltip.y + 15 }}
                    >
                        {tooltip.content}
                    </div>
                )}
            </div>
        </div>
    )
}

export default VisualizationPanel

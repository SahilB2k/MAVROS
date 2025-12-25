// RouteFlow - Enhanced with Click Selection & Hover Tooltips

const API_BASE = window.location.origin

// DOM Elements
const solveBtn = document.getElementById("solve-btn")
const instanceSelect = document.getElementById("instance-select")
const customerCount = document.getElementById("customer-count")
const customerDisplay = document.getElementById("customer-display")
const resultsPanel = document.getElementById("results-panel")
const loadingState = document.getElementById("loading-state")
const routeCanvas = document.getElementById("route-canvas")
const canvasLegend = document.getElementById("canvas-legend")
const routeTooltip = document.getElementById("route-tooltip")

// Result elements
const totalCostEl = document.getElementById("total-cost")
const numVehiclesEl = document.getElementById("num-vehicles")
const solveTimeEl = document.getElementById("solve-time")
const feasibleEl = document.getElementById("feasible")
const routesList = document.getElementById("routes-list")

const ROUTE_COLORS = [
    "#6366F1", "#06B6D4", "#F97316", "#10B981", "#8B5CF6",
    "#EC4899", "#F59E0B", "#14B8A6", "#3B82F6", "#A855F7",
    "#D946EF", "#0EA5E9", "#84CC16", "#06B6D4", "#4F46E5",
]

let currentData = null
let highlightedRoute = null
let selectedRoute = null  // NEW: Locked selection
let animationFrameId = null

// Update customer count display
customerCount.addEventListener("input", (e) => {
    customerDisplay.textContent = e.target.value
})

// Solve button handler
solveBtn.addEventListener("click", async () => {
    const instanceFile = instanceSelect.value
    const maxCustomers = Number.parseInt(customerCount.value)

    solveBtn.disabled = true
    loadingState.classList.add("active")
    routeCanvas.classList.remove("active")
    resultsPanel.classList.add("hidden")
    selectedRoute = null
    highlightedRoute = null

    try {
        const response = await fetch(`${API_BASE}/api/solve`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                instance_file: instanceFile,
                max_customers: maxCustomers,
            }),
        })

        const data = await response.json()

        if (data.success) {
            currentData = data
            displayResults(data)
            visualizeRoutes(data)
            if (data.ortools_baseline) {
                displayComparisonChart(data)
            }
        } else {
            alert(`Error: ${data.error}`)
        }
    } catch (error) {
        alert(`Failed to solve: ${error.message}`)
    } finally {
        solveBtn.disabled = false
        loadingState.classList.remove("active")
    }
})

// Display results
function displayResults(data) {
    totalCostEl.textContent = data.total_cost.toFixed(2)
    numVehiclesEl.textContent = data.num_vehicles
    solveTimeEl.textContent = `${data.solve_time}s`

    feasibleEl.textContent = data.feasible ? "✓ Feasible" : "✗ Infeasible"
    feasibleEl.className = data.feasible ? "stat-badge" : "stat-badge status-infeasible"

    routesList.innerHTML = ""
    data.routes.forEach((route, index) => {
        const routeItem = document.createElement("div")
        routeItem.className = "route-item"
        routeItem.dataset.routeIndex = index
        routeItem.innerHTML = `
      <div class="route-info">
        <div>
          <div class="route-name">Route ${route.route_id}</div>
          <div class="route-details">${route.num_customers} stops • Load: ${route.load}</div>
        </div>
        <div class="route-cost">$${route.cost.toFixed(2)}</div>
      </div>
    `

        // Click to select/lock route
        routeItem.addEventListener('click', () => {
            if (selectedRoute === index) {
                selectedRoute = null  // Deselect
                routeItem.classList.remove('selected')
            } else {
                // Remove previous selection
                document.querySelectorAll('.route-item').forEach(item => item.classList.remove('selected'))
                selectedRoute = index
                routeItem.classList.add('selected')
            }
            visualizeRoutes(currentData)
        })

        // Hover preview (only if not selected)
        routeItem.addEventListener('mouseenter', () => {
            if (selectedRoute === null) {
                setHighlightedRoute(index)
            }
        })

        routeItem.addEventListener('mouseleave', () => {
            if (selectedRoute === null) {
                setHighlightedRoute(null)
            }
        })

        routesList.appendChild(routeItem)
    })

    resultsPanel.classList.remove("hidden")
}

// Display comparison chart
function displayComparisonChart(data) {
    const comparisonSection = document.getElementById('comparison-section')
    if (!comparisonSection) return

    const canvas = document.getElementById('comparison-chart')
    const ctx = canvas.getContext('2d')

    canvas.width = canvas.offsetWidth
    canvas.height = 280

    const custom = {
        cost: data.total_cost,
        vehicles: data.num_vehicles,
        time: data.solve_time
    }

    const ortools = data.ortools_baseline

    const costGap = ((custom.cost - ortools.total_cost) / ortools.total_cost * 100).toFixed(1)
    const speedup = (ortools.solve_time / custom.time).toFixed(1)

    const costGapEl = document.getElementById('cost-gap')
    const speedAdvEl = document.getElementById('speed-advantage')

    if (costGapEl) {
        costGapEl.textContent = `${costGap > 0 ? '+' : ''}${costGap}%`
        costGapEl.style.color = costGap > 0 ? '#F59E0B' : '#10B981'
    }

    if (speedAdvEl) {
        speedAdvEl.textContent = `${speedup}x faster`
        speedAdvEl.style.color = '#10B981'
    }

    const metrics = [
        { label: 'Total Cost', custom: custom.cost, ortools: ortools.total_cost, max: Math.max(custom.cost, ortools.total_cost) * 1.1 },
        { label: 'Vehicles', custom: custom.vehicles, ortools: ortools.num_vehicles, max: Math.max(custom.vehicles, ortools.num_vehicles) + 2 },
        { label: 'Time (s)', custom: custom.time, ortools: ortools.solve_time, max: Math.max(custom.time, ortools.solve_time) * 1.1 }
    ]

    const barHeight = 60
    const barSpacing = 30
    const leftMargin = 100
    const chartWidth = canvas.width - leftMargin - 40

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    metrics.forEach((metric, index) => {
        const y = index * (barHeight + barSpacing) + 20

        ctx.fillStyle = '#F1F5F9'
        ctx.font = 'bold 13px Inter'
        ctx.textAlign = 'right'
        ctx.fillText(metric.label, leftMargin - 15, y + 35)

        const customWidth = (metric.custom / metric.max) * chartWidth
        const gradient1 = ctx.createLinearGradient(leftMargin, 0, leftMargin + customWidth, 0)
        gradient1.addColorStop(0, '#6366F1')
        gradient1.addColorStop(1, '#8B5CF6')

        ctx.fillStyle = gradient1
        ctx.fillRect(leftMargin, y, customWidth, 25)

        ctx.fillStyle = '#F1F5F9'
        ctx.font = 'bold 12px Inter'
        ctx.textAlign = 'left'
        ctx.fillText(metric.custom.toFixed(metric.label === 'Vehicles' ? 0 : 1), leftMargin + customWidth + 8, y + 17)

        const ortoolsWidth = (metric.ortools / metric.max) * chartWidth
        const gradient2 = ctx.createLinearGradient(leftMargin, 0, leftMargin + ortoolsWidth, 0)
        gradient2.addColorStop(0, '#06B6D4')
        gradient2.addColorStop(1, '#14B8A6')

        ctx.fillStyle = gradient2
        ctx.fillRect(leftMargin, y + 30, ortoolsWidth, 25)

        ctx.fillStyle = '#F1F5F9'
        ctx.fillText(metric.ortools.toFixed(metric.label === 'Vehicles' ? 0 : 1), leftMargin + ortoolsWidth + 8, y + 47)
    })

    const legendY = canvas.height - 25

    ctx.fillStyle = '#6366F1'
    ctx.fillRect(leftMargin, legendY, 20, 12)
    ctx.fillStyle = '#F1F5F9'
    ctx.font = '11px Inter'
    ctx.textAlign = 'left'
    ctx.fillText('Custom Solver', leftMargin + 28, legendY + 10)

    ctx.fillStyle = '#06B6D4'
    ctx.fillRect(leftMargin + 140, legendY, 20, 12)
    ctx.fillStyle = '#F1F5F9'
    ctx.fillText('OR-Tools', leftMargin + 168, legendY + 10)

    comparisonSection.classList.remove('hidden')
}

// Set highlighted route
function setHighlightedRoute(index) {
    if (highlightedRoute === index) return

    highlightedRoute = index

    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId)
    }

    animationFrameId = requestAnimationFrame(() => {
        visualizeRoutes(currentData)
    })
}

// Visualize routes with tooltips
function visualizeRoutes(data) {
    const canvas = routeCanvas
    const ctx = canvas.getContext("2d")

    if (canvas.width !== canvas.offsetWidth || canvas.height !== canvas.offsetHeight) {
        canvas.width = canvas.offsetWidth
        canvas.height = canvas.offsetHeight
    }

    const allPoints = [data.depot, ...data.customers]
    const xCoords = allPoints.map((p) => p.x)
    const yCoords = allPoints.map((p) => p.y)
    const minX = Math.min(...xCoords)
    const maxX = Math.max(...xCoords)
    const minY = Math.min(...yCoords)
    const maxY = Math.max(...yCoords)

    const padding = 60
    const scaleX = (canvas.width - 2 * padding) / (maxX - minX || 1)
    const scaleY = (canvas.height - 2 * padding) / (maxY - minY || 1)
    const scale = Math.min(scaleX, scaleY)

    const transform = (x, y) => ({
        x: padding + (x - minX) * scale,
        y: canvas.height - (padding + (y - minY) * scale),
    })

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Determine which route to highlight (selected takes priority)
    const activeRoute = selectedRoute !== null ? selectedRoute : highlightedRoute

    // Draw dimmed routes
    data.routes.forEach((route, index) => {
        if (activeRoute !== null && activeRoute !== index) {
            const color = ROUTE_COLORS[index % ROUTE_COLORS.length]
            ctx.globalAlpha = 0.12
            ctx.strokeStyle = color
            ctx.lineWidth = 2

            ctx.beginPath()
            const depotPos = transform(data.depot.x, data.depot.y)
            ctx.moveTo(depotPos.x, depotPos.y)

            route.customers.forEach((customer) => {
                const pos = transform(customer.x, customer.y)
                ctx.lineTo(pos.x, pos.y)
            })

            ctx.lineTo(depotPos.x, depotPos.y)
            ctx.stroke()

            route.customers.forEach((customer) => {
                const pos = transform(customer.x, customer.y)
                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(pos.x, pos.y, 4, 0, 2 * Math.PI)
                ctx.fill()
            })
        }
    })

    // Draw active/all routes
    ctx.globalAlpha = 1.0
    data.routes.forEach((route, index) => {
        if (activeRoute === null || activeRoute === index) {
            const color = ROUTE_COLORS[index % ROUTE_COLORS.length]
            const isActive = activeRoute === index

            ctx.strokeStyle = color
            ctx.lineWidth = isActive ? 4 : 2.5

            ctx.beginPath()
            const depotPos = transform(data.depot.x, data.depot.y)
            ctx.moveTo(depotPos.x, depotPos.y)

            route.customers.forEach((customer) => {
                const pos = transform(customer.x, customer.y)
                ctx.lineTo(pos.x, pos.y)
            })

            ctx.lineTo(depotPos.x, depotPos.y)
            ctx.stroke()

            route.customers.forEach((customer) => {
                const pos = transform(customer.x, customer.y)
                const radius = isActive ? 6 : 5

                if (isActive) {
                    ctx.fillStyle = color
                    ctx.globalAlpha = 0.3
                    ctx.beginPath()
                    ctx.arc(pos.x, pos.y, 10, 0, 2 * Math.PI)
                    ctx.fill()
                    ctx.globalAlpha = 1.0
                }

                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI)
                ctx.fill()

                ctx.strokeStyle = "#1e293b"
                ctx.lineWidth = 1.5
                ctx.stroke()
            })

            if (isActive) {
                route.customers.forEach((customer) => {
                    const pos = transform(customer.x, customer.y)
                    ctx.fillStyle = "#F1F5F9"
                    ctx.font = "bold 11px Inter"
                    ctx.textAlign = "center"
                    ctx.shadowColor = "rgba(0, 0, 0, 0.8)"
                    ctx.shadowBlur = 4
                    ctx.fillText(customer.id, pos.x, pos.y - 12)
                    ctx.shadowBlur = 0
                })
            }
        }
    })

    // Draw depot
    const depotPos = transform(data.depot.x, data.depot.y)

    ctx.fillStyle = "#EF4444"
    ctx.globalAlpha = 0.3
    ctx.beginPath()
    ctx.arc(depotPos.x, depotPos.y, 18, 0, 2 * Math.PI)
    ctx.fill()

    ctx.globalAlpha = 1.0
    ctx.fillStyle = "#EF4444"
    ctx.beginPath()
    ctx.arc(depotPos.x, depotPos.y, 11, 0, 2 * Math.PI)
    ctx.fill()

    ctx.strokeStyle = "#FFF"
    ctx.lineWidth = 2.5
    ctx.stroke()

    ctx.fillStyle = "#F1F5F9"
    ctx.font = "bold 13px Outfit"
    ctx.shadowColor = "rgba(0, 0, 0, 0.9)"
    ctx.shadowBlur = 6
    ctx.fillText("DEPOT", depotPos.x + 20, depotPos.y)
    ctx.shadowBlur = 0

    canvas.classList.add("active")

    // Setup mouse move for tooltips
    setupCanvasTooltips(canvas, data, transform)

    // Update legend
    if (!canvasLegend.hasChildNodes()) {
        data.routes.forEach((route, index) => {
            const color = ROUTE_COLORS[index % ROUTE_COLORS.length]
            const legendItem = document.createElement("div")
            legendItem.className = "legend-item"
            legendItem.innerHTML = `
        <div class="legend-color" style="background: ${color}"></div>
        <span>Route ${route.route_id} (${route.num_customers} stops)</span>
      `

            legendItem.addEventListener('click', () => {
                if (selectedRoute === index) {
                    selectedRoute = null
                    document.querySelectorAll('.route-item').forEach(item => item.classList.remove('selected'))
                } else {
                    document.querySelectorAll('.route-item').forEach(item => item.classList.remove('selected'))
                    selectedRoute = index
                    document.querySelector(`[data-route-index="${index}"]`).classList.add('selected')
                }
                visualizeRoutes(currentData)
            })

            legendItem.addEventListener('mouseenter', () => {
                if (selectedRoute === null) setHighlightedRoute(index)
            })
            legendItem.addEventListener('mouseleave', () => {
                if (selectedRoute === null) setHighlightedRoute(null)
            })

            canvasLegend.appendChild(legendItem)
        })
        canvasLegend.classList.remove("hidden")
    }
}

// Setup canvas tooltips for route segments
function setupCanvasTooltips(canvas, data, transform) {
    canvas.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect()
        const mouseX = e.clientX - rect.left
        const mouseY = e.clientY - rect.top

        let foundSegment = false

        // Check each route
        data.routes.forEach((route, routeIndex) => {
            if (foundSegment) return

            // Check segments in this route
            for (let i = 0; i < route.customers.length; i++) {
                const customer = route.customers[i]
                const nextCustomer = i < route.customers.length - 1 ? route.customers[i + 1] : null

                const pos1 = transform(customer.x, customer.y)
                const pos2 = nextCustomer ? transform(nextCustomer.x, nextCustomer.y) : transform(data.depot.x, data.depot.y)

                // Check if mouse is near this line segment
                const dist = distanceToSegment(mouseX, mouseY, pos1.x, pos1.y, pos2.x, pos2.y)

                if (dist < 8) {
                    foundSegment = true
                    const distance = customer.distance_to_next
                    const estimatedTime = (distance / 40 * 60).toFixed(1) // Assuming 40 units/hour

                    routeTooltip.innerHTML = `
            <div class="tooltip-header">Route ${routeIndex + 1}</div>
            <div class="tooltip-content">
              <div>📏 Distance: <strong>${distance}</strong> units</div>
              <div>⏱️ Est. Time: <strong>${estimatedTime}</strong> min</div>
              <div>From: <strong>${nextCustomer ? customer.id : customer.id + ' → Depot'}</strong></div>
            </div>
          `
                    routeTooltip.style.left = `${e.clientX + 15}px`
                    routeTooltip.style.top = `${e.clientY + 15}px`
                    routeTooltip.classList.remove('hidden')
                    break
                }
            }
        })

        if (!foundSegment) {
            routeTooltip.classList.add('hidden')
        }
    }

    canvas.onmouseleave = () => {
        routeTooltip.classList.add('hidden')
    }
}

// Calculate distance from point to line segment
function distanceToSegment(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1
    const dy = y2 - y1
    const lengthSquared = dx * dx + dy * dy

    if (lengthSquared === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    let t = ((px - x1) * dx + (py - y1) * dy) / lengthSquared
    t = Math.max(0, Math.min(1, t))

    const projX = x1 + t * dx
    const projY = y1 + t * dy

    return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)
}

console.log("RouteFlow loaded (with Click Selection & Hover Tooltips)")

// Performance Analytics Dashboard - Chart Rendering
// Uses actual benchmark results from verification

const data = {
    custom: {
        cost: 2552.82,
        vehicles: 13,
        time: 27.85,
        memory: 8
    },
    ortools: {
        cost: 1747.00,
        vehicles: 12,
        time: 30.00,
        memory: 150
    }
}

const colors = {
    custom: '#6366F1',
    ortools: '#06B6D4',
    positive: '#10b981',
    negative: '#f59e0b'
}

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function () {
    drawBarChart()
    drawGapChart()
    drawScatterChart()
})

// 1. Bar Chart
function drawBarChart() {
    const canvas = document.getElementById('barChart')
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()

    canvas.width = rect.width * dpr
    canvas.height = 350 * dpr
    canvas.style.width = rect.width + 'px'
    canvas.style.height = '350px'
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = 350
    const padding = 60
    const chartHeight = height - padding * 2

    ctx.clearRect(0, 0, width, height)

    const metrics = [
        { label: 'Cost', custom: data.custom.cost, ortools: data.ortools.cost, max: 3000 },
        { label: 'Vehicles', custom: data.custom.vehicles, ortools: data.ortools.vehicles, max: 15 },
        { label: 'Time (s)', custom: data.custom.time, ortools: data.ortools.time, max: 35 }
    ]

    const barWidth = 50
    const groupWidth = 150
    const startX = (width - (metrics.length * groupWidth)) / 2

    metrics.forEach((metric, i) => {
        const x = startX + i * groupWidth
        const customHeight = (metric.custom / metric.max) * chartHeight
        const ortoolsHeight = (metric.ortools / metric.max) * chartHeight

        // Custom bar
        const grad1 = ctx.createLinearGradient(0, height - padding - customHeight, 0, height - padding)
        grad1.addColorStop(0, colors.custom)
        grad1.addColorStop(1, '#8B5CF6')
        ctx.fillStyle = grad1
        ctx.fillRect(x, height - padding - customHeight, barWidth, customHeight)

        // OR-Tools bar
        const grad2 = ctx.createLinearGradient(0, height - padding - ortoolsHeight, 0, height - padding)
        grad2.addColorStop(0, colors.ortools)
        grad2.addColorStop(1, '#14B8A6')
        ctx.fillStyle = grad2
        ctx.fillRect(x + barWidth + 10, height - padding - ortoolsHeight, barWidth, ortoolsHeight)

        // Values
        ctx.fillStyle = '#F1F5F9'
        ctx.font = 'bold 12px Inter'
        ctx.textAlign = 'center'
        ctx.fillText(metric.custom.toFixed(i === 1 ? 0 : 1), x + barWidth / 2, height - padding - customHeight - 10)
        ctx.fillText(metric.ortools.toFixed(i === 1 ? 0 : 1), x + barWidth + 10 + barWidth / 2, height - padding - ortoolsHeight - 10)

        // Label
        ctx.fillStyle = '#CBD5E1'
        ctx.font = '13px Inter'
        ctx.fillText(metric.label, x + barWidth + 5, height - padding + 30)
    })

    // Legend
    ctx.fillStyle = colors.custom
    ctx.fillRect(startX, 20, 20, 12)
    ctx.fillStyle = '#F1F5F9'
    ctx.font = '12px Inter'
    ctx.textAlign = 'left'
    ctx.fillText('Custom Solver', startX + 28, 30)

    ctx.fillStyle = colors.ortools
    ctx.fillRect(startX + 150, 20, 20, 12)
    ctx.fillText('OR-Tools', startX + 178, 30)
}

// 2. Gap Analysis
function drawGapChart() {
    const canvas = document.getElementById('gapChart')
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()

    canvas.width = rect.width * dpr
    canvas.height = 350 * dpr
    canvas.style.width = rect.width + 'px'
    canvas.style.height = '350px'
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = 350

    ctx.clearRect(0, 0, width, height)

    const gaps = [
        { label: 'Cost Gap', value: ((data.custom.cost - data.ortools.cost) / data.ortools.cost * 100) },
        { label: 'Vehicle Gap', value: ((data.custom.vehicles - data.ortools.vehicles) / data.ortools.vehicles * 100) },
        { label: 'Speed Advantage', value: ((data.ortools.time - data.custom.time) / data.ortools.time * 100) },
        { label: 'Memory Advantage', value: ((data.ortools.memory - data.custom.memory) / data.ortools.memory * 100) }
    ]

    const barHeight = 50
    const spacing = 20
    const leftMargin = 150
    const maxBarWidth = width - leftMargin - 100

    gaps.forEach((gap, i) => {
        const y = 50 + i * (barHeight + spacing)
        const barWidth = Math.abs(gap.value) / 100 * maxBarWidth
        const color = gap.value > 0 ? colors.positive : colors.negative

        // Bar
        ctx.fillStyle = color
        if (gap.value > 0) {
            ctx.fillRect(leftMargin, y, barWidth, barHeight)
        } else {
            ctx.fillRect(leftMargin - barWidth, y, barWidth, barHeight)
        }

        // Label
        ctx.fillStyle = '#F1F5F9'
        ctx.font = 'bold 13px Inter'
        ctx.textAlign = 'right'
        ctx.fillText(gap.label, leftMargin - 15, y + barHeight / 2 + 5)

        // Value
        ctx.textAlign = gap.value > 0 ? 'left' : 'right'
        const textX = gap.value > 0 ? leftMargin + barWidth + 10 : leftMargin - barWidth - 10
        ctx.fillText(`${gap.value > 0 ? '+' : ''}${gap.value.toFixed(1)}%`, textX, y + barHeight / 2 + 5)
    })

    // Zero line
    ctx.strokeStyle = '#CBD5E1'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(leftMargin, 0)
    ctx.lineTo(leftMargin, height)
    ctx.stroke()
}

// 3. Scatter Plot
function drawScatterChart() {
    const canvas = document.getElementById('scatterChart')
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()

    canvas.width = rect.width * dpr
    canvas.height = 350 * dpr
    canvas.style.width = rect.width + 'px'
    canvas.style.height = '350px'
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = 350
    const padding = 80
    const chartWidth = width - 2 * padding
    const chartHeight = height - 2 * padding

    ctx.clearRect(0, 0, width, height)

    const maxCost = 3000
    const maxTime = 35

    // Axes
    ctx.strokeStyle = '#475569'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(padding, padding)
    ctx.lineTo(padding, height - padding)
    ctx.lineTo(width - padding, height - padding)
    ctx.stroke()

    // Grid
    ctx.strokeStyle = '#334155'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    for (let i = 1; i <= 4; i++) {
        const y = padding + (chartHeight / 4) * i
        ctx.beginPath()
        ctx.moveTo(padding, y)
        ctx.lineTo(width - padding, y)
        ctx.stroke()
    }
    ctx.setLineDash([])

    // Points
    const customX = padding + (data.custom.time / maxTime) * chartWidth
    const customY = height - padding - (data.custom.cost / maxCost) * chartHeight
    const ortoolsX = padding + (data.ortools.time / maxTime) * chartWidth
    const ortoolsY = height - padding - (data.ortools.cost / maxCost) * chartHeight

    // OR-Tools point
    ctx.fillStyle = colors.ortools
    ctx.beginPath()
    ctx.arc(ortoolsX, ortoolsY, 12, 0, 2 * Math.PI)
    ctx.fill()
    ctx.strokeStyle = '#FFF'
    ctx.lineWidth = 3
    ctx.stroke()

    // Custom point
    ctx.fillStyle = colors.custom
    ctx.beginPath()
    ctx.arc(customX, customY, 12, 0, 2 * Math.PI)
    ctx.fill()
    ctx.strokeStyle = '#FFF'
    ctx.lineWidth = 3
    ctx.stroke()

    // Labels
    ctx.fillStyle = '#F1F5F9'
    ctx.font = 'bold 12px Inter'
    ctx.textAlign = 'center'
    ctx.fillText('OR-Tools', ortoolsX, ortoolsY - 20)
    ctx.fillText('Custom Solver', customX, customY + 25)

    // Axis labels
    ctx.fillStyle = '#CBD5E1'
    ctx.font = 'bold 14px Inter'
    ctx.fillText('Solve Time (seconds)', width / 2, height - 20)

    ctx.save()
    ctx.translate(20, height / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('Total Cost', 0, 0)
    ctx.restore()
}

// Redraw on resize
window.addEventListener('resize', () => {
    drawBarChart()
    drawGapChart()
    drawScatterChart()
})

/* ==========================================================================
   Dafoor AI - Analytics Component (Vanilla JS)
   ========================================================================== */

export async function renderAnalytics(container, app) {
    let analyticsData = null;

    try {
        analyticsData = await app.apiFetch('/api/analytics');
    } catch (err) {
        app.showToast("Failed to fetch analytics: " + err.message, 'error');
        container.innerHTML = `
            <div class="card" style="text-align: center;">
                <h2>Analytics Error</h2>
                <p>Failed to retrieve score history: ${err.message}</p>
            </div>
        `;
        return;
    }

    const { summary, history } = analyticsData;

    function formatTime(seconds) {
        if (!seconds) return '0m';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        
        if (h > 0) return `${h}h ${m}m`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
    }

    function draw() {
        container.innerHTML = `
            <div>
                <!-- Statistics Row -->
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">Quizzes Taken</span>
                            <div class="stat-val">${summary.total_quizzes}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fa-solid fa-square-poll-vertical"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">Average Score</span>
                            <div class="stat-val">${summary.avg_score}%</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-stopwatch"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">Total Study Time</span>
                            <div class="stat-val">${formatTime(summary.total_time_seconds)}</div>
                        </div>
                    </div>
                </div>

                <!-- Custom Interactive SVG Progress Chart -->
                <div class="card chart-card">
                    <div class="chart-header">
                        <h3><i class="fa-solid fa-chart-line"></i> Score Progress History</h3>
                        <p style="font-size: 0.85rem; color: #6b7280;">Interactive progress timeline</p>
                    </div>
                    
                    <div class="svg-chart-container" id="chart-viewport">
                        <!-- Chart SVG or Empty placeholder -->
                    </div>
                    <div id="chart-tooltip-el" class="chart-tooltip"></div>
                </div>

                <!-- Detailed History Log Table -->
                <div class="card">
                    <h3 class="history-title"><i class="fa-solid fa-clock-rotate-left"></i> Practice History Log</h3>
                    
                    <div class="history-list" id="history-log-container">
                        <!-- History items populated dynamically -->
                    </div>
                </div>
            </div>
        `;

        renderChart();
        renderHistory();
    }

    function renderChart() {
        const viewport = document.getElementById('chart-viewport');
        const tooltip = document.getElementById('chart-tooltip-el');
        
        if (history.length === 0) {
            viewport.innerHTML = `
                <div class="pdf-empty" style="padding-top: 80px;">
                    <i class="fa-solid fa-chart-line" style="font-size: 3rem; margin-bottom: 12px; display: block; opacity: 0.3;"></i>
                    No quiz data available yet. Complete a quiz practice session to map scores!
                </div>
            `;
            return;
        }

        // SVG Chart dimensions
        const width = viewport.clientWidth || 700;
        const height = 280;
        const paddingLeft = 40;
        const paddingRight = 20;
        const paddingTop = 20;
        const paddingBottom = 30;

        const chartWidth = width - paddingLeft - paddingRight;
        const chartHeight = height - paddingTop - paddingBottom;

        // Generate points
        const points = [];
        const numAttempts = history.length;

        history.forEach((attempt, index) => {
            // X spans evenly across attempts
            const x = paddingLeft + (numAttempts > 1 
                ? (index / (numAttempts - 1)) * chartWidth 
                : chartWidth / 2);
            
            // Y spans 0% (bottom of chartHeight) to 100% (top of chartHeight)
            const y = paddingTop + chartHeight - (attempt.score / 100) * chartHeight;
            
            points.push({ x, y, data: attempt });
        });

        // Generate path strings
        let linePath = "";
        let areaPath = "";

        if (points.length === 1) {
            // For a single point, we draw a flat line across the middle of the chart
            const singleY = points[0].y;
            linePath = `M ${paddingLeft} ${singleY} L ${paddingLeft + chartWidth} ${singleY}`;
            areaPath = `M ${paddingLeft} ${singleY} L ${paddingLeft + chartWidth} ${singleY} L ${paddingLeft + chartWidth} ${paddingTop + chartHeight} L ${paddingLeft} ${paddingTop + chartHeight} Z`;
        } else {
            // Multi-point coordinates
            linePath = `M ${points[0].x} ${points[0].y} ` + points.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ');
            
            // Close path at bottom to fill gradient area
            areaPath = `${linePath} L ${points[points.length - 1].x} ${paddingTop + chartHeight} L ${points[0].x} ${paddingTop + chartHeight} Z`;
        }

        // Y-axis grid values
        const gridValues = [0, 25, 50, 75, 100];
        const gridLinesSvg = gridValues.map(val => {
            const y = paddingTop + chartHeight - (val / 100) * chartHeight;
            return `
                <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" class="chart-grid-line" />
                <text x="${paddingLeft - 10}" y="${y + 4}" class="chart-text" text-anchor="end">${val}%</text>
            `;
        }).join('');

        // SVG string construction
        let svgContent = `
            <svg viewBox="0 0 ${width} ${height}" class="chart-svg">
                <defs>
                    <!-- Gradients for styling -->
                    <linearGradient id="chart-gradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="#8b5cf6" />
                        <stop offset="100%" stop-color="#3b82f6" />
                    </linearGradient>
                    <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.4" />
                        <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.0" />
                    </linearGradient>
                </defs>

                <!-- Grid lines -->
                ${gridLinesSvg}

                <!-- X Axis -->
                <line x1="${paddingLeft}" y1="${paddingTop + chartHeight}" x2="${width - paddingRight}" y2="${paddingTop + chartHeight}" class="chart-axis" />

                <!-- Filled Gradient Area -->
                <path d="${areaPath}" class="chart-area" />

                <!-- Main Line -->
                <path d="${linePath}" class="chart-line" />

                <!-- Interactive Data Dots -->
                ${points.map((p, idx) => `
                    <circle 
                        cx="${p.x}" 
                        cy="${p.y}" 
                        r="5" 
                        class="chart-dot" 
                        data-idx="${idx}"
                    />
                `).join('')}
            </svg>
        `;

        viewport.innerHTML = svgContent;

        // Tooltip hover interactive bindings
        viewport.querySelectorAll('.chart-dot').forEach(dot => {
            dot.addEventListener('mouseenter', (e) => {
                const idx = parseInt(dot.getAttribute('data-idx'));
                const pt = points[idx];
                const dateStr = new Date(pt.data.attempted_at).toLocaleDateString();
                
                tooltip.style.opacity = '1';
                tooltip.innerHTML = `
                    <div class="tooltip-title">${pt.data.title}</div>
                    <div style="font-size: 0.8rem; margin: 2px 0; color: #9ca3af;">Date: ${dateStr}</div>
                    <div class="tooltip-score">Score: ${pt.data.score}%</div>
                    <div style="font-size: 0.8rem; color: #9ca3af;">Time: ${formatTime(pt.data.time_spent_seconds)}</div>
                `;

                // Position tooltip above the dot
                const parentBounds = viewport.getBoundingClientRect();
                const dotX = pt.x;
                const dotY = pt.y;

                tooltip.style.left = `${dotX - (tooltip.clientWidth / 2)}px`;
                tooltip.style.top = `${dotY - tooltip.clientHeight - 12}px`;
            });

            dot.addEventListener('mouseleave', () => {
                tooltip.style.opacity = '0';
            });
        });
    }

    function renderHistory() {
        const container = document.getElementById('history-log-container');
        if (history.length === 0) {
            container.innerHTML = `
                <div class="pdf-empty">
                    No quizzes completed yet.
                </div>
            `;
            return;
        }

        // Draw logs in reverse order (newest attempts first)
        const sortedHistory = [...history].reverse();

        container.innerHTML = sortedHistory.map(item => {
            const dateStr = new Date(item.attempted_at).toLocaleString();
            const passStatus = item.score >= 60;
            const scoreClass = passStatus ? '' : 'fail';
            
            return `
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-name">${item.title}</div>
                        <div class="history-meta">
                            <span>Date: ${dateStr}</span> • 
                            <span>Time spent: ${formatTime(item.time_spent_seconds)}</span>
                        </div>
                    </div>
                    <div class="history-score ${scoreClass}">
                        ${item.score}%
                    </div>
                </div>
            `;
        }).join('');
    }

    draw();
}

/* ==========================================================================
   Dafoor AI - Analytics Component (Vanilla JS) — Arabic UI
   ========================================================================== */

export async function renderAnalytics(container, app) {
    let analyticsData = null;

    try {
        analyticsData = await app.apiFetch('/api/analytics');
    } catch (err) {
        app.showToast("فشل تحميل الإحصائيات: " + err.message, 'error');
        container.innerHTML = `
            <div class="card" style="text-align: center;">
                <h2>خطأ في الإحصائيات</h2>
                <p>فشل استرجاع سجل الدرجات: ${err.message}</p>
            </div>
        `;
        return;
    }

    const { summary, history } = analyticsData;

    function formatTime(seconds) {
        if (!seconds) return '0د';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        
        if (h > 0) return `${h}س ${m}د`;
        if (m > 0) return `${m}د ${s}ث`;
        return `${s}ث`;
    }

    function draw() {
        container.innerHTML = `
            <div>
                <!-- Statistics Row -->
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">الاختبارات المُنجزة</span>
                            <div class="stat-val">${summary.total_quizzes}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fa-solid fa-square-poll-vertical"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">متوسط الدرجات</span>
                            <div class="stat-val">${summary.avg_score}%</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fa-solid fa-stopwatch"></i></div>
                        <div class="stat-info">
                            <span class="stat-label">إجمالي وقت الدراسة</span>
                            <div class="stat-val">${formatTime(summary.total_time_seconds)}</div>
                        </div>
                    </div>
                </div>

                <!-- Custom Interactive SVG Progress Chart -->
                <div class="card chart-card">
                    <div class="chart-header">
                        <h3><i class="fa-solid fa-chart-line"></i> سجل تقدم الدرجات</h3>
                        <p style="font-size: 0.85rem; color: #6b7280;">خط زمني تفاعلي للتقدم</p>
                    </div>
                    
                    <div class="svg-chart-container" id="chart-viewport">
                        <!-- Chart SVG or Empty placeholder -->
                    </div>
                    <div id="chart-tooltip-el" class="chart-tooltip"></div>
                </div>

                <!-- Detailed History Log Table -->
                <div class="card">
                    <h3 class="history-title"><i class="fa-solid fa-clock-rotate-left"></i> سجل جلسات التدريب</h3>
                    
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
                    لا توجد بيانات اختبارات بعد. أكمل جلسة تدريب لعرض الدرجات هنا!
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
            const singleY = points[0].y;
            linePath = `M ${paddingLeft} ${singleY} L ${paddingLeft + chartWidth} ${singleY}`;
            areaPath = `M ${paddingLeft} ${singleY} L ${paddingLeft + chartWidth} ${singleY} L ${paddingLeft + chartWidth} ${paddingTop + chartHeight} L ${paddingLeft} ${paddingTop + chartHeight} Z`;
        } else {
            linePath = `M ${points[0].x} ${points[0].y} ` + points.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ');
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
                const dateStr = new Date(pt.data.attempted_at).toLocaleDateString('ar-SA');
                
                tooltip.style.opacity = '1';
                tooltip.innerHTML = `
                    <div class="tooltip-title">${pt.data.title}</div>
                    <div style="font-size: 0.8rem; margin: 2px 0; color: #9ca3af;">التاريخ: ${dateStr}</div>
                    <div class="tooltip-score">الدرجة: ${pt.data.score}%</div>
                    <div style="font-size: 0.8rem; color: #9ca3af;">الوقت: ${formatTime(pt.data.time_spent_seconds)}</div>
                `;

                // Position tooltip above the dot
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
                    لم تُكمل أي اختبارات بعد.
                </div>
            `;
            return;
        }

        // Draw logs in reverse order (newest attempts first)
        const sortedHistory = [...history].reverse();

        container.innerHTML = sortedHistory.map(item => {
            const dateStr = new Date(item.attempted_at).toLocaleString('ar-SA');
            const passStatus = item.score >= 60;
            const scoreClass = passStatus ? '' : 'fail';
            
            return `
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-name">${item.title}</div>
                        <div class="history-meta">
                            <span>التاريخ: ${dateStr}</span> • 
                            <span>الوقت المستغرق: ${formatTime(item.time_spent_seconds)}</span>
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

const charts = {};

const createOrUpdateChart = (
    chartId, data, buysell, ema_study, macd_study, bbm_study, rsi_study, adx_study, candle_trend_study, timeUnit
) => {
    const datasets = [];
    const scales = {}; // Dynamic y-axis configuration

    const studyColors = {
        ema_slow: 'rgba(0, 123, 255, 0.7)',    // Blue for EMA Slow
        ema_medium: 'rgba(255, 123, 0, 0.7)',  // Orange for EMA Medium
        ema_fast: 'rgba(0, 255, 123, 0.7)',    // Green for EMA Fast
        macd_line: 'rgba(255, 0, 0, 0.7)',     // Red for MACD Line
        macd_signal: 'rgba(123, 0, 255, 0.7)', // Purple for MACD Signal
        macd_histogram: 'rgba(123, 123, 123, 0.7)', // Gray for Histogram
        bbl: 'rgba(0, 0, 255, 0.7)',           // Dark Blue for BBL
        bbm: 'rgba(26, 26, 17, 0.7)',         // Dark Gray for BBM
        bbu: 'rgba(0, 123, 0, 0.7)',            // Green for BBU
        rsi_slow: 'rgba(112, 91, 99, 0.7)',    // Purple for RSI Slow
        rsi_fast: 'rgba(156, 23, 23, 0.7)',    // Red for RSI Fast  
    };

    const mapOptionalData = (data, key, yKey = key.replace('_', '')) => {
        return data.filter(d => typeof d[key] !== 'undefined' && parseFloat(d[key]) !== 0).map(d => ({
            x: parseInt(d.time),
            y: parseFloat(d[key])
        }));
    };


    // Candlestick Data
    scales['y-axis'] = {
        type: 'linear',
        position: 'left',
        title: { display: true, text: 'CandleStick' }
    };

    datasets.push({
        type: 'candlestick',
        label: 'Candlestick Data',
        data: data.map(d => ({
            x: parseInt(d.time),
            o: parseFloat(d.open),
            h: parseFloat(d.high),
            l: parseFloat(d.low),
            c: parseFloat(d.close)
        })),
        borderColor: 'rgba(0, 0, 0, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        yAxisID: 'y-axis' // Unique y-axis ID
    });

    // EMA Study
    if (ema_study) {
        datasets.push({
            label: 'EMA Slow',
            data: mapOptionalData(data, 'ma_slow'),
            backgroundColor: studyColors.ema_slow,
            borderColor: studyColors.ema_slow,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis',
            hidden: true
        });
    
        datasets.push({
            label: 'EMA Medium',
            data: mapOptionalData(data, 'ma_medium'),
            backgroundColor: studyColors.ema_medium,
            borderColor: studyColors.ema_medium,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis'
        });

        datasets.push({
            label: 'EMA Fast',
            data: mapOptionalData(data, 'ma_fast'),
            backgroundColor: studyColors.ema_fast,
            borderColor: studyColors.ema_fast,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis'
        });
    }

    // BBM Study
    if (bbm_study) {
        datasets.push({
            label: 'BBU',
            data: mapOptionalData(data, 'BBU'),
            backgroundColor: studyColors.bbu,
            borderColor: studyColors.bbu,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis'
        });

        datasets.push({
            label: 'BBM',
            data: mapOptionalData(data, 'BBM'),
            backgroundColor: studyColors.bbm,
            borderColor: studyColors.bbm,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis'
        });

        datasets.push({
            label: 'BBL',
            data: mapOptionalData(data, 'BBL'),
            backgroundColor: studyColors.bbl,
            borderColor: studyColors.bbl,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis'
        });
    }

    // MACD Study
    if (macd_study) {

        scales['y-axis-macd'] = {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'MACD' }
        };

        datasets.push({
            label: 'MACD Line',
            data: mapOptionalData(data, 'MACD_Line'),
            backgroundColor: studyColors.macd_line,
            borderColor: studyColors.macd_line,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-macd'
        });

        datasets.push({
            label: 'MACD Signal',
            data: mapOptionalData(data, 'MACD_Signal'),
            backgroundColor: studyColors.macd_signal,
            borderColor: studyColors.macd_signal,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-macd'
        });

        scales['y-axis-macd-histogram'] = {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'MACD Histogram' }
        };
        datasets.push({
            label: 'MACD Histogram',
            data: mapOptionalData(data, 'MACD_Histogram'),
            backgroundColor: studyColors.macd_histogram,
            borderColor: studyColors.macd_histogram,
            borderWidth: 0,
            type: 'bar',
            yAxisID: 'y-axis-macd-histogram',
            hidden: true
        });
    }

    // RSI Study
    if (rsi_study) {

        scales['y-axis-rsi'] = {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'RSI' }
        };

        datasets.push({
            label: 'RSI SLOW',
            data: mapOptionalData(data, 'rsi_slow'),
            backgroundColor: studyColors.rsi_slow,
            borderColor: studyColors.rsi_slow,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-rsi'
        });

        datasets.push({
            label: 'RSI FAST',
            data: mapOptionalData(data, 'rsi_fast'),
            backgroundColor: studyColors.rsi_fast,
            borderColor: studyColors.rsi_fast,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-rsi'
        });
    }

    // Find the min and max time from candlestickData
    const times = data.map(d => d.x);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    // Buy/Sell data points
    datasets.push(...buysell.filter(d => {
        const time = parseInt(d.ctime);
        return time >= minTime && time <= maxTime;
    }).map(d => ({
        label: d.side === 'BUY' ? 'Buy' : 'Sell',
        data: [{ x: parseInt(d.ctime), y: parseFloat(d.price) }],
        backgroundColor: d.side === 'BUY' ? 'rgba(0, 255, 0, 0.9)' : 'rgba(255, 0, 0, 0.9)',
        borderColor: d.side === 'BUY' ? 'rgba(0, 255, 0, 1)' : 'rgba(255, 0, 0, 1)',
        borderWidth: 2,
        pointStyle: 'triangle',
        pointRadius: 5,
        yAxisID: 'y-axis'
    })));

    const timeSettings = {
        second: { unit: 'second', stepSize: 1, displayFormats: { second: 'HH:mm:ss' } },
        minute: { unit: 'minute', stepSize: 1, displayFormats: { minute: 'HH:mm' } },
        hour: { unit: 'hour', stepSize: 1, displayFormats: { hour: 'HH:mm' } },
        day: { unit: 'day', stepSize: 1, displayFormats: { day: 'MMM dd' } }
    };

    // Define chart configuration
    const chartConfig = {
        type: 'candlestick',
        data: { datasets },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: { unit: timeUnit, stepSize: 1, displayFormats: { second: 'HH:mm:ss', minute: 'HH:mm', hour: 'HH:mm', day: 'MMM dd' } }
                },
                ...scales // Dynamically include y-axis configurations
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            // Handle cases where context.parsed might be undefined
                            if (!context.parsed) {
                                return `${context.dataset.label}: Data unavailable`;
                            }
                
                            const x = context.parsed.x !== undefined ? context.parsed.x : 'N/A';
                            const y = context.parsed.y !== undefined ? context.parsed.y : 'N/A';
                
                            // Check if the dataset is candlestick
                            if (context.dataset.type === 'candlestick') {
                                const o = context.raw.o !== undefined ? context.raw.o : 'N/A'; // Open
                                const h = context.raw.h !== undefined ? context.raw.h : 'N/A'; // High
                                const l = context.raw.l !== undefined ? context.raw.l : 'N/A'; // Low
                                const c = context.raw.c !== undefined ? context.raw.c : 'N/A'; // Close
                                return `${context.dataset.label}: (Open: ${o}, High: ${h}, Low: ${l}, Close: ${c})`;
                            }
                
                            // Default for other datasets
                            return `${context.dataset.label}: (${x}, ${y})`;
                        }
                    }
                }
                
            }
        }
    };

    // Render or update the chart
    if (charts[chartId]) {
        // Assign only the 'data' of the specified dataset (indexed by x)
        chartConfig.data.datasets.forEach((dataset, index) => {
            if (charts[chartId].data.datasets[index]) {
                charts[chartId].data.datasets[index].data = dataset.data; // Update only the data property
            }
        });
        charts[chartId].options = chartConfig.options;
        charts[chartId].update();
    }
    else {
        const ctx = document.getElementById(chartId).getContext('2d');
        charts[chartId] = new Chart(ctx, chartConfig);
    }
};



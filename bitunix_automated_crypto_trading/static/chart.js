
const charts = {};
let candlestickContainer, macdContainer, rsiContainer;

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

const timeSettings = {
    second: { unit: 'second', stepSize: 1, displayFormats: { second: 'HH:mm:ss' } },
    minute: { unit: 'minute', stepSize: 1, displayFormats: { minute: 'HH:mm' } },
    hour: { unit: 'hour', stepSize: 1, displayFormats: { hour: 'HH:mm' } },
    day: { unit: 'day', stepSize: 1, displayFormats: { day: 'MMM dd' } }
};


const createOrUpdateChart = (
    chartId, data, buysell, ema_study, ema_display, macd_study, macd_display, bbm_study, bbm_display, rsi_study, rsi_display, timeUnit
) => {
    const candlestickChartId=`${chartId}-candlestick`;
    const timeConfig = timeSettings[timeUnit] || timeSettings['second'];

    const mapOptionalData = (data, key, slopeKey='') => {
        return data.filter(d => typeof d[key] !== 'undefined' && parseFloat(d[key]) !== 0).map(d => ({
            x: parseInt(d.time),
            y: parseFloat(d[key]),
            slope: slopeKey ? parseFloat(d[slopeKey]) : null, // Optional slope value
            label: key,
            time: new Date(parseInt(d.time)).toLocaleString('en-US', {
                year: 'numeric',
                month: 'numeric',
                day: 'numeric',
                hour: 'numeric',
                minute: 'numeric',
                second: 'numeric',
                hour12: false // Use 24-hour time format
            })
        }));
    };

    slowMA = mapOptionalData(data, 'ma_slow');
    mediumMA = mapOptionalData(data, 'ma_medium', 'ma_medium_slope');
    fastMA = mapOptionalData(data, 'ma_fast');
    macdLine = mapOptionalData(data, 'MACD_Line');
    signalLine = mapOptionalData(data, 'MACD_Signal');
    macdHistogram = mapOptionalData(data, 'MACD_Histogram');
    BBL = mapOptionalData(data, 'BBL');
    BBM = mapOptionalData(data, 'BBM');
    BBU = mapOptionalData(data, 'BBU');
    rsi_slow = mapOptionalData(data, 'rsi_slow');
    rsi_fast = mapOptionalData(data, 'rsi_fast');


    function findHighestStartTime(dataArrays) {
        let highestStartTime = 0;
        dataArrays.forEach(dataArray => {
            if (dataArray && dataArray.length > 0) {
                const startTime = new Date(dataArray[0].x).getTime(); // Parse time to timestamp
                if (startTime > highestStartTime) {
                    highestStartTime = startTime;
                }
            }
        });
        return highestStartTime;
    }
    
    const allDataArrays = [
        slowMA, mediumMA, fastMA, macdLine, signalLine, macdHistogram,
        BBL, BBM, BBU, rsi_slow, rsi_fast
    ];

    // Find the highest start time
    const highestStartTime = findHighestStartTime(allDataArrays);''

    // Filter all data arrays based on the highest start time
    slowMA = slowMA.filter(d => parseInt(d.x) >= highestStartTime)
    mediumMA = mediumMA.filter(d => parseInt(d.x) >= highestStartTime)
    fastMA = fastMA.filter(d => parseInt(d.x) >= highestStartTime)
    macdLine = macdLine.filter(d => parseInt(d.x) >= highestStartTime)
    signalLine = signalLine.filter(d => parseInt(d.x) >= highestStartTime)
    macdHistogram = macdHistogram.filter(d => parseInt(d.x) >= highestStartTime)
    BBL = BBL.filter(d => parseInt(d.x) >= highestStartTime)
    BBM = BBM.filter(d => parseInt(d.x) >= highestStartTime)
    BBU = BBU.filter(d => parseInt(d.x) >= highestStartTime)
    rsi_slow = rsi_slow.filter(d => parseInt(d.x) >= highestStartTime)
    rsi_fast = rsi_fast.filter(d => parseInt(d.x) >= highestStartTime)


    const candlestickData = data
        .filter(d => parseInt(d.time) >= highestStartTime) // Filter data
        .map(d => ({
        x: parseInt(d.time),
        o: parseFloat(d.open),
        h: parseFloat(d.high),
        l: parseFloat(d.low),
        c: parseFloat(d.close),
        y: parseFloat(d.close),
        time: new Date(parseInt(d.time)).toLocaleString('en-US', {
            year: 'numeric',
            month: 'numeric',
            day: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric',
            hour12: false // Use 24-hour time format
        })
}));

    const buyselldata = buysell
        .filter(d => parseInt(d.ctime) >= highestStartTime) // Filter data
        .map(d => ({
        x: parseInt(d.ctime),
        y: parseFloat(d.price),
        qty: parseFloat(d.qty),
        side: d.side,
        time: new Date(parseInt(d.ctime)).toLocaleTimeString('en-US', { hour: 'numeric', minute: 'numeric', second: 'numeric', hour12: false }),
        backgroundColor: d.side === 'BUY' ? 'rgba(3, 735, 0, 0.9)' : 'rgba(228, 48, 48, 0.9)', // Color based on buy/sell
        borderColor: d.side === 'BUY' ? 'rgb(3, 73, 3)' : 'rgba(255, 0, 0, 1)',
        borderWidth: 2,
        pointRadius: 2, // Increased for better visibility
        pointStyle: 'circle' // Changed for better visibility
    }));

    // main chart /////////////////////////////////////////////////////////////////////////////////////////
    const datasets = [];
    const scales = {}; // Dynamic y-axis configuration

    // Candlestick Data
    scales['y-axis-candlestick'] = {
        type: 'linear',
        position: 'left',
        title: { display: true, text: 'CandleStick' },
        ticks: {
            callback: (value) => value, // default
            labelMaxWidth: 100, // Add this for fixed width
        },
        afterFit: (scale) => {  // set fixed width of the scale
            scale.width = 100; // Or any other value
        }
    };

    datasets.push({
        type: 'candlestick',
        label: 'Candlestick Data',
        data: candlestickData,
        borderColor: 'rgba(0, 0, 0, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        yAxisID: 'y-axis-candlestick' // Unique y-axis ID
    });

    // EMA Study (on the candlestick chart)
    if (ema_study) {
        datasets.push({
            label: 'EMA Slow',
            data: slowMA,
            backgroundColor: studyColors.ema_slow,
            borderColor: studyColors.ema_slow,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !ema_display
        });

        datasets.push({
            label: 'EMA Medium',
            data: mediumMA,
            backgroundColor: studyColors.ema_medium,
            borderColor: studyColors.ema_medium,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !ema_display // Hide if not displayed
        });

        datasets.push({
            label: 'EMA Fast',
            data: fastMA,
            backgroundColor: studyColors.ema_fast,
            borderColor: studyColors.ema_fast,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !ema_display // Hide if not displayed
        });
    }

    // BBM Study (on the candlestick chart)
    if (bbm_study) {
        datasets.push({
            label: 'BBU',
            data: BBU,
            backgroundColor: studyColors.bbu,
            borderColor: studyColors.bbu,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !bbm_display // Hide if not displayed
        });

        datasets.push({
            label: 'BBM',
            data: BBM,
            backgroundColor: studyColors.bbm,
            borderColor: studyColors.bbm,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !bbm_display // Hide if not displayed
        });

        datasets.push({
            label: 'BBL',
            data: BBL,
            backgroundColor: studyColors.bbl,
            borderColor: studyColors.bbl,
            borderWidth: 1,
            fill: false,
            type: 'line',
            pointRadius: 0,
            yAxisID: 'y-axis-candlestick',
            hidden: !bbm_display // Hide if not displayed
        });
    }
    
    // Buy/Sell data points (on the candlestick chart)
    datasets.push({
        label: 'BuySell',
        data: buyselldata,
        type: 'scatter',
        backgroundColor: buyselldata.map(d => d.backgroundColor),
        borderColor: buyselldata.map(d => d.borderColor),
        borderWidth: buyselldata.map(d => d.borderWidth),
        pointRadius: buyselldata.map(d => d.pointRadius),
        pointStyle: buyselldata.map(d => d.pointStyle),
        yAxisID: 'y-axis-candlestick' // Unique y-axis ID
    });

    // Define main candlestick chart configuration
    const chartConfig = {
        type: 'candlestick',
        data: { datasets },
        options: {
            responsive: true,
            animation: false,
            maintainAspectRatio: false,
            transitions: {
                show: {
                    animations: {
                        colors: { from: 'transparent' },
                    },
                },
                hide: {
                    animations: {
                        colors: { to: 'transparent' },
                    },
                },
            },
            scales: {
                    x: {
                        type: 'time',
                        time: timeConfig,
                        ticks: {
                            major: {
                                enabled: true,
                            },
                        }
                  },
                    ...scales // Dynamically include y-axis configurations
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    enabled: false,
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true // Enable zooming with the mouse wheel
                        },
                        pinch: {
                            enabled: true // Enable pinch-to-zoom
                        },
                        mode: 'xy' // Allow zooming in both directions
                    },
                    pan: {
                        enabled: true, // Enable panning
                        mode: 'xy' // Allow panning in both directions
                    }
                }
            }
        }
    };

    // Render or update the main candlestick chart
    if (charts[candlestickChartId]) {
        // Assign only the 'data' of the specified dataset (indexed by x)
        chartConfig.data.datasets.forEach((dataset, index) => {
            if (charts[candlestickChartId].data.datasets[index]) {
                charts[candlestickChartId].data.datasets[index].data = dataset.data; // Update only the data property
            }
        });
        charts[candlestickChartId].options = chartConfig.options;
        charts[candlestickChartId].update();
    }
    else {
        if (charts[candlestickChartId]) {
            charts[candlestickChartId].destroy(); // Destroy the existing chart instance
            delete charts[candlestickChartId]
        }

        candlestickContainer = document.querySelector(`.chart-container#${candlestickChartId}`);
        candlestickContainer.innerHTML = "";
        const newCanvas = document.createElement('canvas');
        newCanvas.id = candlestickChartId;
        candlestickContainer.appendChild(newCanvas);

        const ctx = newCanvas.getContext('2d');
        charts[candlestickChartId] = new Chart(ctx, chartConfig);
    
        //crosshair 
        const chartArea = document.querySelector(`.chart-area#${chartId}`);
        const verticalCrosshair = document.createElement('div');
        const horizontalCrosshair = document.createElement('div');
        // Style the crosshair
        verticalCrosshair.style.position = 'absolute';
        verticalCrosshair.style.width = '1px';
        verticalCrosshair.style.height = `${chartArea.offsetHeight}px`; // Match the height of chart-area
        verticalCrosshair.style.backgroundColor = 'red';
        verticalCrosshair.style.display = 'none';
        chartArea.appendChild(verticalCrosshair);
        horizontalCrosshair.style.position = 'absolute';
        horizontalCrosshair.style.height = '1px';
        horizontalCrosshair.style.width = `${chartArea.offsetWidth}px`; // Match the width of chart-area
        horizontalCrosshair.style.backgroundColor = 'red';
        horizontalCrosshair.style.display = 'none';
        chartArea.appendChild(horizontalCrosshair);
    
        // Create a value content box to show values
        const valueContent = document.createElement('div');
        valueContent.className = 'value-content';
        valueContent.style.position = 'absolute';
        valueContent.style.backgroundColor = 'rgba(255, 255, 255, 0.5)';
        valueContent.style.border = '1px solid black';
        valueContent.style.padding = '5px';
        chartArea.appendChild(valueContent);
    
        // Add mousemove event listener
        chartArea.addEventListener('mousemove', event => {
            const chartAreaRect = chartArea.getBoundingClientRect();
            const mouseX = event.clientX;
            const mouseY = event.clientY;
            const relativeX = event.clientX - chartAreaRect.left;
            const relativeY = event.clientY - chartAreaRect.top;
            const chartAreaWidth = chartArea.offsetWidth;
            const chartAreaHeight = chartArea.offsetHeight;

            // Ensure the crosshair stays within the chart-area
            if (relativeX >= 0 && relativeX <= chartAreaRect.width) {
                verticalCrosshair.style.left = `${relativeX}px`;
                verticalCrosshair.style.height = `${chartAreaRect.height}px`;
                verticalCrosshair.style.display = 'block';
            } else {
                verticalCrosshair.style.display = 'none';
            }
    
            if (relativeY >= 0 && relativeY <= chartAreaRect.height) {
                horizontalCrosshair.style.top = `${relativeY}px`;
                horizontalCrosshair.style.width = `${chartAreaRect.width}px`;
                horizontalCrosshair.style.display = 'block';
            } else {
                horizontalCrosshair.style.display = 'none';
            }
            
            const values = getValuesAtCrosshairPosition(chartId, relativeX);
    
            valueContent.style.width = 'auto'; // Adjust width as needed
            valueContent.style.height = 'auto'; // Adjust height as needed
            valueContent.innerHTML = `<strong>${chartId}</strong><br>`; // Clear previous content
            valueContent.innerHTML += `<strong>${values[0].values[0].value.time}</strong><br>`; // Clear previous content
            if (values.length > 0) {
    
                // Populate the box with values
                for (let i = 0; i < values.length; i++) {
                    const chartData = values[i].values;
                    const chartLabel = values[i].label;
                    for (let j = 0; j < chartData.length; j++) {
                        const dataPoint = chartData[j];
                        if (dataPoint.value === undefined) {
                            continue; // Skip if value is undefined
                        }
                        if (chartLabel.includes('-candlestick')) {
                            if (dataPoint.label === 'Candlestick Data') {
                                valueContent.innerHTML += `${dataPoint.label}: o:${dataPoint.value.o.toFixed(4)}, h:${dataPoint.value.h.toFixed(4)}, l:${dataPoint.value.l.toFixed(4)}, c:${dataPoint.value.c.toFixed(4)}<br>`;
                            } else if(dataPoint.label === 'BuySell'){
                                valueContent.innerHTML += `${dataPoint.label}: ${dataPoint.value.side}, qty: ${dataPoint.value.qty}, price: ${dataPoint.value.y} <br>`;
                            } else {
                                valueContent.innerHTML += `${dataPoint.label}: ${dataPoint.value.y.toFixed(4)}, slope: ${dataPoint.value.slope ? dataPoint.value.slope.toFixed(8) : 'N/A'} <br>`;
                            }
                        }
                        if (chartLabel.includes('-macd')) {
                            valueContent.innerHTML += `${dataPoint.label}: ${dataPoint.value.y.toFixed(4)}<br>`;
                        }
                        if (chartLabel.includes('-rsi')) {
                            valueContent.innerHTML += `${dataPoint.label}: ${dataPoint.value.y.toFixed(4)}<br>`;
                        }
                    }
                }   

                const padding = 20
                valueContent.style.display = 'block';

                // Get the width and height
                const valueBoxWidth = valueContent.offsetWidth;
                const valueBoxHeight = valueContent.offsetHeight;
        
        
                // Adjust position if close to the right edge
                let boxX = relativeX + 10; // Default position to the right
                if (relativeX + valueBoxWidth + padding > chartAreaWidth) {
                    boxX = relativeX - valueBoxWidth - 10; // Position box on the left
                }
        
                // Adjust position if close to the bottom edge
                let boxY = relativeY + 10; // Default position below
                if (relativeY + valueBoxHeight + padding > chartAreaHeight) {
                    boxY = relativeY - valueBoxHeight - 10; // Position box on top
                }

                valueContent.style.left = `${boxX}px`;
                valueContent.style.top = `${boxY}px`;
            }
    
        });
        
        // Optional: Add mouseleave event to hide the crosshair when the cursor leaves chart-area
        chartArea.addEventListener('mouseleave', () => {
            verticalCrosshair.style.display = 'none';
            horizontalCrosshair.style.display = 'none';
            valueContent.style.display = 'none';
        });
    
    }


    // bottom charts /////////////////////////////////////////////////////////////////////////////////////////
    // MACD Study (separate chart)
    if (macd_study) {
        macdContainer = createOrUpdateSubChart(
            `${chartId}-macd`,
            ['macd-line', 'macd-signal', 'macd-histogram'],
            macdLine,
            signalLine,
            macdHistogram,
            macd_display,
            timeConfig, // <--- Same timeConfig
            'macdChart',
            'MACD'
        );
    } else {
        destroySubChart('macdChart');
    }
    
    if (rsi_study) {
        rsiContainer = createOrUpdateSubChart(
            `${chartId}-rsi`,
            ['rsi-slow', 'rsi-fast', ''],
            rsi_slow,
            rsi_fast,
            null,
            rsi_display,
            timeConfig, // <--- Same timeConfig
            'rsiChart',
            'RSI'
        );
    } else {
        destroySubChart('rsiChart');
    }
    // Set the heights of the charts based on the ratios
    if (candlestickContainer && macdContainer && rsiContainer) {
        const chartRatio = 6; // Ratio for the main chart
        const macdRatio = 2; // Ratio for the MACD chart
        const rsiRatio = 2; // Ratio for the RSI chart
        const totalRatio = chartRatio + macdRatio + rsiRatio;
        const chartHeight = 100 / totalRatio; // Calculate the height percentage for each chart
        candlestickContainer.style.flex = chartRatio;
        macdContainer.style.flex = macdRatio;
        rsiContainer.style.flex = rsiRatio;
    }
}

function createOrUpdateSubChart(chartId, labels, lineData1, lineData2, barData, isDisplayed, timeConfig, canvasId, chartTitle){
    let container
    const datasets = [];
    const scales = {};

    scales['y-axis'] = {
        type: 'linear',
        position: 'left',
        title: { display: true, text: chartTitle },
        ticks: {
            callback: (value) => value, // default
            labelMaxWidth: 100, // Add this for fixed width
        },
        afterFit: (scale) => {  // set fixed width of the scale
            scale.width = 100; // Or any other value
        }    
    };

    if (lineData1 && isDisplayed) {
        datasets.push({
            type: 'line',
            label: labels[0],
            data: lineData1,
            borderColor: studyColors[`${chartTitle.toLowerCase().replace(' ', '_')}_line`] || 'blue',
            borderWidth: 1,
            fill: false,
            pointRadius: 0,
            yAxisID: 'y-axis'
        });
    }
    if (lineData2 && isDisplayed) {
        datasets.push({
            type: 'line',
            label:  labels[1],
            data: lineData2,
            borderColor: studyColors[`${chartTitle.toLowerCase().replace(' ', '_')}_signal`] || 'red',
            borderWidth: 1,
            fill: false,
            pointRadius: 0,
            yAxisID: 'y-axis'
        });
    }
    if (barData && isDisplayed) {
        scales['y-axis-bar'] = {
            type: 'linear',
            position: 'right',
            title: { display: false, text: `${chartTitle} Histogram` },
            grid: { drawOnChartArea: false },
            ticks: {  // Add this ticks property
                display: false  // Set display to false to hide the scale ticks/labels
            }
        };
        datasets.push({
            type: 'bar',
            label: labels[2],
            data: barData,
            backgroundColor: studyColors[`${chartTitle.toLowerCase().replace(' ', '_')}_histogram`] || 'gray',
            pointRadius: 0,
            yAxisID: 'y-axis-bar'
        });
    }

    const chartConfig = {
        type: barData ? 'bar' : 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            transitions: {
                show: {
                    animations: {
                        colors: { from: 'transparent' },
                    },
                },
                hide: {
                    animations: {
                        colors: { to: 'transparent' },
                    },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: timeConfig, // Use the SAME timeConfig for both MACD and RSI
                    ticks: {
                        major: {
                            enabled: true 
                        },
                    }
                },
                ...scales
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    enabled: false,
                }
            },
            zoom: {
                zoom: {
                    wheel: {
                        enabled: true // Enable zooming with the mouse wheel
                    },
                    pinch: {
                        enabled: true // Enable pinch-to-zoom
                    },
                    mode: 'xy' // Allow zooming in both directions
                },
                pan: {
                    enabled: true, // Enable panning
                    mode: 'xy' // Allow panning in both directions
                }
            }

        }
    };

    if (charts[canvasId]) {
        charts[canvasId].data = chartConfig.data;
        charts[canvasId].options = chartConfig.options;
        charts[canvasId].update();
    } else {
        container = document.querySelector(`.chart-container#${chartId}`);
        if (container) {
            container.innerHTML = "";
            const newCanvas = document.createElement('canvas');
            newCanvas.id = chartId;
            container.appendChild(newCanvas);
            const ctx = newCanvas.getContext('2d');
            charts[chartId] = new Chart(ctx, chartConfig);
        } else {
            console.error(`Chart container with id "${chartId}" not found.`);
        }
    }
    return container;
};


const destroySubChart = (chartId) => {
    if (charts[chartId]) {
        charts[chartId].destroy();
        delete charts[chartId];
        const chartContainer = document.querySelector(`.chart-container#${chartId}`);
        if (chartContainer) {
            chartContainer.innerHTML = ""; // Clear the container
        }
    }
};


function getValuesAtCrosshairPosition(chartid, crosshairX) {
    let chartDataAtX = [];
    
    for (let chart in charts) {
        if (!chart.includes(chartid)) continue;
        const xScale = charts[chart].scales.x; // Access the X-axis scale
        const datasets = charts[chart].data.datasets; // Access chart datasets

        // Get the pixel position for each data point
        let nearestIndex = null;
        let minDistance = Infinity;

        datasets.forEach(dataset => {
            dataset.data.forEach((dataPoint, index) => {
                const dataX = xScale.getPixelForValue(dataPoint.x); // Get pixel for each data point
                
                // Find the nearest data point to the crosshair
                const distance = Math.abs(crosshairX - dataX);
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestIndex = index; // Track the closest data index
                }
            });
        });

        // Collect data for the nearest index
        if (nearestIndex !== null) {
            let valuesAtIndex = datasets.map(dataset => ({
                label: dataset.label,
                value: dataset.data[nearestIndex] // Use the nearest index to fetch the value
            }));

            chartDataAtX.push({
                label: chart,
                values: valuesAtIndex
            });
        }
    }

    return chartDataAtX;
}
  
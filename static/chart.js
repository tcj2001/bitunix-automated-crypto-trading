const charts = {};

const createOrUpdateChart = (chartId, chartData, buySellData, timeUnit = 'second', chartOptions = {}, datasetColors = {}) => {
    const candlestickData = chartData.map(d => ({
        x: parseInt(d.time),
        o: parseFloat(d.open),
        h: parseFloat(d.high),
        l: parseFloat(d.low),
        c: parseFloat(d.close)
    }));

    const mapOptionalData = (data, key, yKey = key.replace('_', '')) => {
        return data.filter(d => typeof d[key] !== 'undefined' && parseFloat(d[key]) !== 0).map(d => ({
            x: parseInt(d.time),
            y: parseFloat(d[key])
        }));
    };

    const slowMA = mapOptionalData(chartData, 'ma_slow');
    const mediumMA = mapOptionalData(chartData, 'ma_medium');
    const fastMA = mapOptionalData(chartData, 'ma_fast');
    const macdLine = mapOptionalData(chartData, 'MACD_Line');
    const signalLine = mapOptionalData(chartData, 'MACD_Signal');
    const macdHistogram = mapOptionalData(chartData, 'MACD_Histogram');
    const BBL = mapOptionalData(chartData, 'BBL');
    const BBM = mapOptionalData(chartData, 'BBM');
    const BBU = mapOptionalData(chartData, 'BBU');

    // Find the min and max time from candlestickData
    const times = candlestickData.map(d => d.x);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    const buyselldata = buySellData.filter(d => {
        const time = parseInt(d.ctime);
        return time >= minTime && time <= maxTime;
    }).map(d => ({
        x: parseInt(d.ctime),
        y: parseFloat(d.price),
        side: d.side,
        backgroundColor: d.side === 'BUY' ? 'rgba(0, 255, 0, 0.9)' : 'rgba(255, 0, 0, 0.9)', // Color based on buy/sell
        borderColor: d.side === 'BUY' ? 'rgba(0, 255, 0, 1)' : 'rgba(255, 0, 0, 1)',
        borderWidth: 2,
        pointRadius: 5, // Increased for better visibility
        pointStyle: 'triangle' // Changed for better visibility
    }));

    const timeSettings = {
        second: { unit: 'second', stepSize: 1, displayFormats: { second: 'HH:mm:ss' } },
        minute: { unit: 'minute', stepSize: 1, displayFormats: { minute: 'HH:mm' } },
        hour: { unit: 'hour', stepSize: 1, displayFormats: { hour: 'HH:mm' } },
        day: { unit: 'day', stepSize: 1, displayFormats: { day: 'MMM dd' } }
    };

    const timeConfig = timeSettings[timeUnit] || timeSettings['second'];

    const defaultDatasetColors = {
        slowMA: { borderColor: 'rgba(255, 99, 132, 1)', backgroundColor: 'rgba(255, 99, 132, 0.2)' },
        mediumMA: { borderColor: 'rgba(54, 162, 235, 1)', backgroundColor: 'rgba(54, 162, 235, 0.2)' },
        fastMA: { borderColor: 'rgb(2, 12, 12)', backgroundColor: 'rgba(4, 15, 15, 0.2)' },
        macdLine: { borderColor: 'blue' },
        signalLine: { borderColor: 'red' },
        macdHistogram: { backgroundColor: 'green' },
        bbl: { borderColor: 'black' },
        bbm: { borderColor: 'green' },
        bbu: { borderColor: 'brown' },
    };

    const mergedDatasetColors = {
        slowMA: { ...defaultDatasetColors.slowMA, ...datasetColors.slowMA },
        mediumMA: { ...defaultDatasetColors.mediumMA, ...datasetColors.mediumMA },
        fastMA: { ...defaultDatasetColors.fastMA, ...datasetColors.fastMA },
        macdLine: { ...defaultDatasetColors.macdLine, ...datasetColors.macdLine },
        signalLine: { ...defaultDatasetColors.signalLine, ...datasetColors.signalLine },
        macdHistogram: { ...defaultDatasetColors.macdHistogram, ...datasetColors.macdHistogram },
        bbl: { ...defaultDatasetColors.bbl, ...datasetColors.bbl },
        bbm: { ...defaultDatasetColors.bbm, ...datasetColors.bbm },
        bbu: { ...defaultDatasetColors.bbu, ...datasetColors.bbu },
    };

    if (charts[chartId]) {
        const chartn = charts[chartId];
        chartn.data.datasets[0].data = candlestickData;
        chartn.data.datasets[1].data = slowMA;
        chartn.data.datasets[2].data = mediumMA;
        chartn.data.datasets[3].data = fastMA;
        chartn.data.datasets[4].data = macdLine;
        chartn.data.datasets[5].data = signalLine;
        chartn.data.datasets[6].data = macdHistogram;
        chartn.data.datasets[7].data = buyselldata;
        chartn.data.datasets[8].data = BBL;
        chartn.data.datasets[9].data = BBM;
        chartn.data.datasets[10].data = BBU;
        chartn.update();
    } else {
        const ctx = document.getElementById(chartId).getContext('2d');
        charts[chartId] = new Chart(ctx, {
            type: 'candlestick',
            data: {
                datasets: [
                    {
                        label: chartId,
                        data: candlestickData,
                        type: 'candlestick',
                        order: 1,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: false
                    },
                    {
                        label: 'Slow MA',
                        data: slowMA,
                        borderColor: mergedDatasetColors.slowMA.borderColor,
                        backgroundColor: mergedDatasetColors.slowMA.backgroundColor,
                        type: 'line',
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 2,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'Medium MA',
                        data: mediumMA,
                        borderColor: mergedDatasetColors.mediumMA.borderColor,
                        backgroundColor: mergedDatasetColors.mediumMA.backgroundColor,
                        type: 'line',
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 3,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'Fast MA',
                        data: fastMA,
                        borderColor: mergedDatasetColors.fastMA.borderColor,
                        backgroundColor: mergedDatasetColors.fastMA.backgroundColor,
                        type: 'line',
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 4,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'MACD Line',
                        type: 'line',
                        data: macdLine,
                        borderColor: mergedDatasetColors.macdLine.borderColor,
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 5,
                        yAxisID: 'y2',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'Signal Line',
                        type: 'line',
                        data: signalLine,
                        borderColor: mergedDatasetColors.signalLine.borderColor,
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 6,
                        yAxisID: 'y2',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'MACD Histogram',
                        type: 'bar',
                        data: macdHistogram,
                        backgroundColor: mergedDatasetColors.macdHistogram.backgroundColor,
                        order: 7,
                        borderWidth: 0, // No border for histogram bars
                        yAxisID: 'y3',
                        xAxisID: 'x',
                        hidden: true
                    },
                    {
                        label: 'BuySell',
                        data: buyselldata,
                        type: 'scatter',
                        showLine: false,
                        order: 8,
                        backgroundColor: buyselldata.map(d => d.backgroundColor),
                        borderColor: buyselldata.map(d => d.borderColor),
                        borderWidth: buyselldata.map(d => d.borderWidth),
                        pointRadius: buyselldata.map(d => d.pointRadius),
                        pointStyle: buyselldata.map(d => d.pointStyle),
                        hidden: false
                    },
                    {
                        label: 'BBL',
                        type: 'line',
                        data: BBL,
                        borderColor: mergedDatasetColors.bbl.borderColor,
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 9,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: false
                    },
                    {
                        label: 'BBM',
                        type: 'line',
                        data: BBM,
                        borderColor: mergedDatasetColors.bbm.borderColor,
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 10,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: false
                    },
                    {
                        label: 'BBU',
                        type: 'line',
                        data: BBU,
                        borderColor: mergedDatasetColors.bbu.borderColor,
                        pointRadius: 0,
                        borderWidth: 1,
                        fill: false,
                        order: 11,
                        yAxisID: 'y',
                        xAxisID: 'x',
                        hidden: false
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const datasetIndex = context.datasetIndex;
                                const dataIndex = context.dataIndex;
                                if (datasetIndex === 0) { // Candlestick dataset
                                    const data = chartData[dataIndex];
                                    return [
                                        `Time: ${data.time}`,
                                        `Open: ${data.open}`,
                                        `High: ${data.high}`,
                                        `Low: ${data.low}`,
                                        `Close: ${data.close}`
                                    ];
                                } else if (datasetIndex === 7) { // BuySell dataset
                                    const data = buySellData[dataIndex];
                                    return [
                                        `Time: ${data.ctime}`,
                                        `Price: ${data.price}`,
                                        `Side: ${data.side}`
                                    ];
                                } else {
                                    return `${context.dataset.label}: ${context.raw.y}`;
                                }
                            }
                        }
                    },
                    zoom: {
                        pan: {
                            enabled: true,
                            mode: 'x'
                        },
                        zoom: {
                            enabled: true,
                            mode: 'x'
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: timeConfig,
                        stacked: false
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Price'
                        },
                        grid: {
                            drawOnChartArea: true
                        }
                    },
                    y2: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'MACD'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    y3: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'MACD Hist'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                layout: {
                    padding: {
                        top: 20,
                        bottom: 20,
                        left: 10,
                        right: 30 // Make space for the second y-axis title
                    }
                },
                ...chartOptions // Override default options
            }
        });
    }
};
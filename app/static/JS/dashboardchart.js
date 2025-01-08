// Declare global variables for Chart.js instances
let cpuUsageChart = null;
let memoryUsageChart = null;

// Store datasets indexed by server IP for dynamic updates
const cpuUsageDatasets = {};
const memoryUsageDatasets = {};

// Store the initial load time to use as the reference point for the x-axis
let initialLoadTime = new Date();

// Function to fetch metrics from API and update charts
async function fetchAllAgentMetrics() {
    try {
        const response = await axios.get('/api/metrics/all');
        const metrics = response.data;

        const currentTime = new Date(); // Use the current time for x-axis

        metrics.forEach(metric => {
            // Validate the structure of each metric object
            if (!metric || !metric.metrics) {
                console.warn("Invalid metric object:", metric);
                return; // Skip this metric
            }

            const serverIp = metric.ip;
            const cpuUsage = parseFloat(metric.metrics.cpu_total); // CPU percentage
            const memoryUsage = parseFloat(metric.metrics.memory); // Memory usage

            // Update CPU Usage Chart
            if (!cpuUsageDatasets[serverIp]) {
                const newDataset = {
                    label: `Server ${serverIp}`,
                    data: [], // Initialize empty data
                    borderWidth: 1,
                    borderColor: getRandomColor(),
                    backgroundColor: 'rgba(0, 0, 0, 0)', // Transparent fill
                    tension: 0.6,
                    pointRadius: 3,
                    pointHoverRadius: 5
                };
                cpuUsageDatasets[serverIp] = newDataset;
                if (cpuUsageChart) cpuUsageChart.data.datasets.push(newDataset);
            }

            // Add data to the server's dataset
            cpuUsageDatasets[serverIp].data.push({ x: currentTime, y: cpuUsage });
            if (cpuUsageDatasets[serverIp].data.length > 100) {
                cpuUsageDatasets[serverIp].data.shift(); // Keep the latest 100 points
            }

            // Update Memory Usage Chart
            if (!memoryUsageDatasets[serverIp]) {
                const newDataset = {
                    label: `Server ${serverIp}`,
                    data: [],
                    borderWidth: 1,
                    borderColor: getRandomColor(),
                    backgroundColor: 'rgba(0, 0, 0, 0)', // Transparent fill
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 5
                };
                memoryUsageDatasets[serverIp] = newDataset;
                if (memoryUsageChart) memoryUsageChart.data.datasets.push(newDataset);
            }

            // Add data to the server's dataset
            memoryUsageDatasets[serverIp].data.push({ x: currentTime, y: memoryUsage });
            if (memoryUsageDatasets[serverIp].data.length > 50) {
                memoryUsageDatasets[serverIp].data.shift(); // Keep the latest 50 points
            }
        });

        // Update charts
        if (cpuUsageChart) cpuUsageChart.update();
        if (memoryUsageChart) memoryUsageChart.update();
    } catch (error) {
        console.error('Error fetching metrics for all agents:', error);
    }
}

// Helper function to generate random colors for datasets
function getRandomColor() {
    const r = Math.floor(Math.random() * 255);
    const g = Math.floor(Math.random() * 255);
    const b = Math.floor(Math.random() * 255);
    return `rgba(${r}, ${g}, ${b}, 1)`;
}

// Function to initialize the charts
function initializeCharts() {
    const ctxCpu = document.getElementById('cpuUsageChart');
    const ctxMemory = document.getElementById('memoryUsageChart');

    if (ctxCpu) {
        cpuUsageChart = new Chart(ctxCpu.getContext('2d'), {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest',
                    intersect: false
                },
                plugins: {
                    zoom: {
                        pan: {
                            enabled: true,
                            mode: 'x'
                        },
                        zoom: {
                            wheel: {
                                enabled: true
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x',
                            limits: {
                                x: {
                                    min: () => initialLoadTime,
                                    max: () => new Date()
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'second',
                            displayFormats: {
                                second: 'HH:mm:ss'
                            },
                            tooltipFormat: 'MMM dd, HH:mm:ss'
                        },
                        ticks: {
                            autoSkip: true,
                            maxTicksLimit: 10
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'CPU Usage (%)'
                        }
                    }
                }
            }
        });
    }

    if (ctxMemory) {
        memoryUsageChart = new Chart(ctxMemory.getContext('2d'), {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest',
                    intersect: false
                },
                plugins: {
                    zoom: {
                        pan: {
                            enabled: true,
                            mode: 'x'
                        },
                        zoom: {
                            wheel: {
                                enabled: true
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x',
                            limits: {
                                x: {
                                    min: () => initialLoadTime,
                                    max: () => new Date()
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'second',
                            displayFormats: {
                                second: 'HH:mm:ss'
                            },
                            tooltipFormat: 'MMM dd, HH:mm:ss'
                        },
                        ticks: {
                            autoSkip: true,
                            maxTicksLimit: 10
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Memory Usage (GB)'
                        }
                    }
                }
            }
        });
    }

    // Add event listeners for reset buttons
    document.getElementById('resetCpuZoomButton').addEventListener('click', () => {
        if (cpuUsageChart) {
            cpuUsageChart.resetZoom();
        }
    });

    document.getElementById('resetMemoryZoomButton').addEventListener('click', () => {
        if (memoryUsageChart) {
            memoryUsageChart.resetZoom();
        }
    });
}

// Initialize the charts on page load
window.addEventListener('load', initializeCharts);

// Periodically fetch metrics
setInterval(fetchAllAgentMetrics, 2000);

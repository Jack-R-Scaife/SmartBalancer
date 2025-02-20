document.addEventListener("DOMContentLoaded", function () {
  // Chart variables and dataset storage
  let cpuUsageChart = null;
  let memoryUsageChart = null;
  let responseTimeChart = null;
  let groupsLookup = {};  // maps group_id to group name
  let groupsData = [];    // groups retrieved from API
  let cpuUsageDatasets = {};
  let memoryUsageDatasets = {};
  let responseTimeDatasets = {};
  let colorMapping  = {};

  // Track filter settings separately for CPU, Memory, and Response Time charts
  let currentCpuFilter = { group: "all", server: "all" };
  let currentMemoryFilter = { group: "all", server: "all" };
  let currentResponseFilter = { group: "all", server: "all" };

  const predefinedColors = [
    // Reds/Pinks
    "#FF6B6B", // Coral Red
    "#FF69B4", // Hot Pink
    "#FF1493", // Deep Pink
    
    // Oranges/Salmon
    "#FFA500", // Pure Orange
    "#FF6347", // Tomato
    "#FA8072", // Salmon
    "#FF4500", // Orange-Red
    
    // Greens
    "#3CB371", // Medium Sea Green
    "#32CD32", // Lime Green
    "#00FA9A", // Medium Spring Green
    
    // Blues/Purples
    "#4ECDC4", // Medium Turquoise
    "#45B7D1", // Sky Blue
    "#6A5ACD", // Slate Blue
    "#8A2BE2", // Blue Violet
    "#9370DB", // Medium Purple
    
    // Yellows
    "#FFEEAD", // Light Yellow
    "#FFD700", // Gold
    
    // Others
    "#C23B22", // Rust Red
    "#DA70D6", // Orchid
    "#4B0082", // Indigo
    "#D2691E"  // Chocolate
  ];
  
  // Replace assignColorsToGroups with this new version
  function assignColorsToGroups(groups) {
    // Helper to generate hash-based index from string
    function stringToColorIndex(str) {
      let hash = 5381; // Initial prime number
      for (let i = 0; i < str.length; i++) {
        hash = (hash << 9) - hash + str.charCodeAt(i);
      }
      return Math.abs(hash) % predefinedColors.length;
    }
  
    const usedColors = new Set();
  
    function getUniqueColor(key) {
      let index = stringToColorIndex(key);
      let attempts = 0;
      
      while (attempts < predefinedColors.length) {
        const color = predefinedColors[index];
        if (!usedColors.has(color)) {
          usedColors.add(color);
          return color;
        }
        index = (index + 1) % predefinedColors.length;
        attempts++;
      }
      return "#cccccc"; // Fallback if all colors exhausted
    }
  
    groups.forEach(group => {
      const groupAvgKey = `${group.name}_Average`;
      colorMapping[groupAvgKey] = getUniqueColor(groupAvgKey);
  
      if (group.servers) {
        group.servers.forEach(server => {
          const serverKey = `${group.name}_${server.ip}`;
          colorMapping[serverKey] = getUniqueColor(serverKey);
        });
      }
    });
  
    colorMapping["Overall"] = "#FFFFFF";
  }
  
  

  // Retrieve an assigned color based on the label.
  function getAssignedColor(label) {
    return colorMapping[label] || "#cccccc"; // fallback to light gray
  }

  // ---------------------------
  // Chart Initialization Functions
  // ---------------------------
  
  function initializeCharts() {
    const ctxCpu = document.getElementById("cpuUsageChart");
    const ctxMemory = document.getElementById("memoryUsageChart");
  
    if (ctxCpu) {
      cpuUsageChart = new Chart(ctxCpu.getContext("2d"), {
        type: "line",
        data: { datasets: [] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          aspectRatio: 2,
          layout: { padding: { top: 10, bottom: 35 } },
          scales: {
            x: {
              type: "time",
              offset: true, // centers points on ticks
              time: {
                unit: "second",
                displayFormats: { second: "HH:mm:ss" },
                tooltipFormat: "MMM dd, HH:mm:ss"
              },
              ticks: { autoSkip: true, maxTicksLimit: 5, maxRotation: 0, minRotation: 0, font: { size: 12 } },
              title: { display: true, text: "Time", font: { size: 12 } }
            },
            y: {
              beginAtZero: true,
              ticks: { font: { size: 12 } },
              title: { display: true, text: "CPU Usage (%)", font: { size: 12 } }
            }
          },
          plugins: {
            zoom: {
              pan: { enabled: true, mode: "x" },
              zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" }
            }
          }
        }
      });
    }
  
    if (ctxMemory) {
      memoryUsageChart = new Chart(ctxMemory.getContext("2d"), {
        type: "line",
        data: { datasets: [] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          aspectRatio: 2,
          layout: { padding: { top: 10, bottom: 35 } },
          scales: {
            x: {
              type: "time",
              offset: true,
              time: {
                unit: "second",
                displayFormats: { second: "HH:mm:ss" },
                tooltipFormat: "MMM dd, HH:mm:ss"
              },
              ticks: { autoSkip: true, maxTicksLimit: 5, maxRotation: 0, minRotation: 0, font: { size: 12 } },
              title: { display: true, text: "Time", font: { size: 12 } }
            },
            y: {
              beginAtZero: true,
              ticks: { font: { size: 12 } },
              title: { display: true, text: "Memory Usage GB (%)", font: { size: 12 } }
            }
          },
          plugins: {
            zoom: {
              pan: { enabled: true, mode: "x" },
              zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" }
            }
          }
        }
      });
    }
  }
  
  function initializeResponseTimeChart() {
    const ctx = document.getElementById("responseTimeChart");
    if (ctx) {
      responseTimeChart = new Chart(ctx.getContext("2d"), {
        type: "line",
        data: { datasets: [] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          aspectRatio: 1,
          layout: { padding: { top: 5, bottom: 25 } },
          scales: {
            x: {
              type: "time",
              offset: true,
              time: { unit: "second", displayFormats: { second: "HH:mm:ss" }, tooltipFormat: "MMM dd, HH:mm:ss" },
              ticks: { autoSkip: true, maxTicksLimit: 5, maxRotation: 0, minRotation: 0, font: { size: 12 } },
              title: { display: true, text: "Time", font: { size: 12 } }
            },
            y: {
              beginAtZero: true,
              ticks: { font: { size: 12 } },
              title: { display: true, text: "Response Time (ms)", font: { size: 12 } }
            }
          },
          plugins: {
            zoom: {
              pan: { enabled: true, mode: "x" },
              zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" }
            }
          }
        }
      });
    }
  }
  
  // ---------------------------
  // Dropdown Population Functions
  // ---------------------------
  
  function populateGroupDropdowns(groups) {
    groupsData = groups;
    const cpuGroupDropdown = document.getElementById("cpuUsageGroup");
    const memoryGroupDropdown = document.getElementById("memoryUsageGroup");
    cpuGroupDropdown.innerHTML = '<option value="all">All Groups</option>';
    memoryGroupDropdown.innerHTML = '<option value="all">All Groups</option>';
    groups.forEach(group => {
      const cpuOption = new Option(group.name, group.group_id);
      cpuGroupDropdown.add(cpuOption);
      const memOption = new Option(group.name, group.group_id);
      memoryGroupDropdown.add(memOption);
    });
    cpuGroupDropdown.addEventListener("change", updateCpuServerDropdown);
    memoryGroupDropdown.addEventListener("change", updateMemoryServerDropdown);
  }
  
  function populateResponseTimeDropdowns(groups) {
    rtGroupsData = groups;
    const rtGroupDropdown = document.getElementById("responsetimeGroup");
    const rtServerDropdown = document.getElementById("responsetimeServer");
    if (!rtGroupDropdown || !rtServerDropdown) {
      console.error("Response Time dropdown elements missing.");
      return;
    }
    rtGroupDropdown.innerHTML = '<option value="all">All Groups</option>';
    groups.forEach(group => {
      const option = new Option(group.name, group.group_id);
      rtGroupDropdown.add(option);
    });
    rtGroupDropdown.value = "all";
    rtServerDropdown.innerHTML = '<option value="all">All Servers</option>';
    rtServerDropdown.value = "all";
    rtGroupDropdown.addEventListener("change", updateResponseTimeServerDropdown);
    rtServerDropdown.addEventListener("change", function () {
      clearResponseTimeChartData();
      fetchResponseTimeMetrics();
    });
  }
  
  function updateCpuServerDropdown() {
    const selectedGroupId = document.getElementById("cpuUsageGroup").value;
    const cpuServerDropdown = document.getElementById("cpuUsageServer");
    cpuServerDropdown.innerHTML = '<option value="all">All Servers</option>';
    if (selectedGroupId === "all") {
      groupsData.forEach(group => {
        if (group.servers && Array.isArray(group.servers)) {
          group.servers.forEach(server => {
            const option = new Option(server.ip, server.ip);
            cpuServerDropdown.add(option);
          });
        }
      });
    } else {
      const group = groupsData.find(g => g.group_id == selectedGroupId);
      if (group && group.servers) {
        group.servers.forEach(server => {
          const option = new Option(server.ip, server.ip);
          cpuServerDropdown.add(option);
        });
      }
    }
    clearCpuChartData();
    fetchCpuMetrics();
  }
  
  function updateMemoryServerDropdown() {
    const selectedGroupId = document.getElementById("memoryUsageGroup").value;
    const memoryServerDropdown = document.getElementById("memoryUsageServer");
    memoryServerDropdown.innerHTML = '<option value="all">All Servers</option>';
    if (selectedGroupId === "all") {
      groupsData.forEach(group => {
        if (group.servers && Array.isArray(group.servers)) {
          group.servers.forEach(server => {
            const option = new Option(server.ip, server.ip);
            memoryServerDropdown.add(option);
          });
        }
      });
    } else {
      const group = groupsData.find(g => g.group_id == selectedGroupId);
      if (group && group.servers) {
        group.servers.forEach(server => {
          const option = new Option(server.ip, server.ip);
          memoryServerDropdown.add(option);
        });
      }
    }
    clearMemoryChartData();
    fetchMemoryMetrics();
  }
  
  function updateResponseTimeServerDropdown() {
    const selectedGroupId = document.getElementById("responsetimeGroup").value;
    const rtServerDropdown = document.getElementById("responsetimeServer");
    rtServerDropdown.innerHTML = '<option value="all">All Servers</option>';
    if (selectedGroupId === "all") {
      rtGroupsData.forEach(group => {
        if (group.servers && Array.isArray(group.servers)) {
          group.servers.forEach(server => {
            const option = new Option(server.ip, server.ip);
            rtServerDropdown.add(option);
          });
        }
      });
    } else {
      const group = rtGroupsData.find(g => g.group_id == selectedGroupId);
      if (group && group.servers) {
        group.servers.forEach(server => {
          const option = new Option(server.ip, server.ip);
          rtServerDropdown.add(option);
        });
      }
    }
    clearResponseTimeChartData();
    fetchResponseTimeMetrics();
  }
  
  // ---------------------------
  // Chart Data Update Functions
  // ---------------------------
  
  function getCpuFilter() {
    return {
      group: document.getElementById("cpuUsageGroup").value,
      server: document.getElementById("cpuUsageServer").value
    };
  }
  function getMemoryFilter() {
    return {
      group: document.getElementById("memoryUsageGroup").value,
      server: document.getElementById("memoryUsageServer").value
    };
  }
  function getResponseTimeFilter() {
    return {
      group: document.getElementById("responsetimeGroup").value,
      server: document.getElementById("responsetimeServer").value
    };
  }
  
  function clearCpuChartData() {
    if (cpuUsageChart) {
      cpuUsageChart.data.datasets = [];
      cpuUsageDatasets = {};
    }
  }
  function clearMemoryChartData() {
    if (memoryUsageChart) {
      memoryUsageChart.data.datasets = [];
      memoryUsageDatasets = {};
    }
  }
  function clearResponseTimeChartData() {
    if (responseTimeChart) {
      responseTimeChart.data.datasets = [];
      responseTimeDatasets = {};
    }
  }
  
  // This function aggregates metrics.
  // For "all/all": overall average.
  // For a specific group with "all servers": average of that group's servers.
  // For a specific server: that server's metric.
  function processMetrics(metrics, selectedGroupId, selectedServerIp, metricKey) {
    const currentTime = new Date();
    
    // Get group name from lookup
    const groupName = groupsLookup[selectedGroupId] || "Unknown";
  
    if (selectedGroupId === "all" && selectedServerIp === "all") {
      return [{
        label: "Overall",
        value: calculateAverage(metrics, metricKey),
        time: currentTime
      }];
    }
  
    if (selectedGroupId !== "all" && selectedServerIp === "all") {
      return [{
        label: `${groupName}_Average`,
        value: calculateGroupAverage(metrics, selectedGroupId, metricKey),
        time: currentTime
      }];
    }
  
    if (selectedServerIp !== "all") {
      const serverMetric = metrics.find(m => m.ip === selectedServerIp);
      return serverMetric ? [{
        label: `${groupName}_${serverMetric.ip}`,
        value: parseFloat(serverMetric.metrics[metricKey]),
        time: currentTime
      }] : [];
    }
  
    return [];
  }
  
  function calculateAverage(metrics, metricKey) {
    const total = metrics.reduce((sum, metric) => sum + parseFloat(metric.metrics[metricKey] || 0), 0);
    return metrics.length > 0 ? total / metrics.length : 0;
  }
  
  function calculateGroupAverage(metrics, groupId, metricKey) {
    const group = groupsData.find(g => String(g.group_id) === String(groupId));
    if (!group?.servers) return 0;
    
    const serverIps = group.servers.map(s => s.ip);
    const groupMetrics = metrics.filter(m => serverIps.includes(m.ip));
    return calculateAverage(groupMetrics, metricKey);
  }
  function updateChart(chart, datasets, data) {
    data.forEach(item => {
      if (!datasets[item.label]) {
        datasets[item.label] = {
          label: item.label,
          data: [],
          borderColor: getAssignedColor(item.label),
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.4
        };
      }
      // Keep only last 60 data points (5 minutes at 5s intervals)
      if (datasets[item.label].data.length >= 60) {
        datasets[item.label].data.shift();
      }
      datasets[item.label].data.push({ x: item.time, y: item.value });
    });
  
    // Sort datasets to maintain consistent order
    chart.data.datasets = Object.values(datasets).sort((a, b) => 
      a.label.localeCompare(b.label)
    );
    
    chart.update();
  }
  
  function fetchCpuMetrics() {
    let newFilter = getCpuFilter();
    if (newFilter.group !== currentCpuFilter.group || newFilter.server !== currentCpuFilter.server) {
      clearCpuChartData();
      currentCpuFilter = newFilter;
    }
    fetch("/api/metrics/all")
      .then(response => response.json())
      .then(metrics => {
        const cpuData = processMetrics(
          metrics,
          document.getElementById("cpuUsageGroup").value,
          document.getElementById("cpuUsageServer").value,
          "cpu_total"
        );
        updateChart(cpuUsageChart, cpuUsageDatasets, cpuData);
      })
      .catch(error => console.error("Error fetching CPU metrics:", error));
  }
  
  function fetchMemoryMetrics() {
    let newFilter = getMemoryFilter();
    if (newFilter.group !== currentMemoryFilter.group || newFilter.server !== currentMemoryFilter.server) {
      clearMemoryChartData();
      currentMemoryFilter = newFilter;
    }
    fetch("/api/metrics/all")
      .then(response => response.json())
      .then(metrics => {
        const memoryData = processMetrics(
          metrics,
          document.getElementById("memoryUsageGroup").value,
          document.getElementById("memoryUsageServer").value,
          "memory"
        );
        updateChart(memoryUsageChart, memoryUsageDatasets, memoryData);
      })
      .catch(error => console.error("Error fetching Memory metrics:", error));
  }
  
  function fetchResponseTimeMetrics() {
    let newFilter = getResponseTimeFilter();
    if (newFilter.group !== currentResponseFilter.group || newFilter.server !== currentResponseFilter.server) {
      clearResponseTimeChartData();
      currentResponseFilter = newFilter;
    }
    fetch("/api/ping_agents")
      .then(response => response.json())
      .then(data => {
        const filter = getResponseTimeFilter();
        // Process using a specialized function
        const rtData = processResponseTimeMetrics(data, filter.group, filter.server);
        updateChart(responseTimeChart, responseTimeDatasets, rtData);
      })
      .catch(error => console.error("Error fetching response time metrics:", error));
  }
  
  // Specialized function for response time.
  function processResponseTimeMetrics(data, selectedGroupId, selectedServerIp) {
    const currentTime = new Date();
    const groupName = groupsLookup[selectedGroupId] || "Unknown";
  
    if (selectedGroupId === "all" && selectedServerIp === "all") {
      const total = data.response_times.reduce((sum, agent) => sum + parseFloat(agent.response_time || 0), 0);
      const count = data.response_times.length;
      const avg = count > 0 ? total / count : 0;
      return [{ label: "Overall", value: avg, time: currentTime }];
    } else if (selectedGroupId !== "all" && selectedServerIp === "all") {
      const groupObj = groupsData.find(g => String(g.group_id) === selectedGroupId);
      if (groupObj && groupObj.servers) {
        const serverIps = groupObj.servers.map(s => s.ip);
        const groupAgents = data.response_times.filter(agent => serverIps.includes(agent.ip));
        const total = groupAgents.reduce((sum, agent) => sum + parseFloat(agent.response_time || 0), 0);
        const count = groupAgents.length;
        const avg = count > 0 ? total / count : 0;
        return [{ label: `${groupName}_Average`, value: avg, time: currentTime }]; // Changed here
      }
      return [{ label: `${groupName}_Average`, value: 0, time: currentTime }];
    } else if (selectedServerIp !== "all") {
      const agent = data.response_times.find(agent => agent.ip === selectedServerIp);
      return agent ? [{
        label: `${groupName}_${agent.ip}`,  // Changed here
        value: parseFloat(agent.response_time), 
        time: currentTime
      }] : [];
    }
    return [];
  }
  
  // ---------------------------
  // Initialization and Polling
  // ---------------------------
  
  // Initialize CPU and Memory charts.
  initializeCharts();
  // Fetch groups, assign colors, and populate dropdowns.
  fetch("/api/get_groups")
    .then(response => response.json())
    .then(data => {
      if (data.status === "success") {
        groupsData = data.groups;
        data.groups.forEach(group => {
          groupsLookup[group.group_id] = group.name;
        });
        assignColorsToGroups(data.groups);
        populateGroupDropdowns(data.groups);
        populateResponseTimeDropdowns(data.groups);
        console.log("Color Mapping:", colorMapping);
        const colorCounts = {};
      Object.values(colorMapping).forEach(color => {
        colorCounts[color] = (colorCounts[color] || 0) + 1;
      });
      console.log("Color Usage Counts:", colorCounts);
        // Set default dropdowns for CPU and Memory.
        document.getElementById("cpuUsageGroup").value = "all";
        document.getElementById("cpuUsageServer").innerHTML = '<option value="all">All Servers</option>';
        document.getElementById("memoryUsageGroup").value = "all";
        document.getElementById("memoryUsageServer").innerHTML = '<option value="all">All Servers</option>';
      }
    })
    .catch(error => console.error("Error fetching groups:", error));
  
  // Initialize Response Time chart.
  initializeResponseTimeChart();
  
  // Immediate data fetch.
  fetchCpuMetrics();
  fetchMemoryMetrics();
  fetchResponseTimeMetrics();
  
  // Polling intervals.
  setInterval(fetchCpuMetrics, 2000);
  setInterval(fetchMemoryMetrics, 2000);
  setInterval(fetchResponseTimeMetrics, 2000);
  
  // Reset zoom event listeners.
  document.getElementById("resetCpuZoomButton").addEventListener("click", () => {
    if (cpuUsageChart) cpuUsageChart.resetZoom();
  });
  document.getElementById("resetMemoryZoomButton").addEventListener("click", () => {
    if (memoryUsageChart) memoryUsageChart.resetZoom();
  });
  document.getElementById("resetResponseZoomButton").addEventListener("click", () => {
    if (responseTimeChart) responseTimeChart.resetZoom();
  });
  
  // ---------------------------
  // Other Charts (Traffic, Prediction Efficiency, Active Connections, Strategy)
  // ---------------------------
  
  // Traffic Chart
  const t24C = document.getElementById("traffic24Chart").getContext("2d");
  const trafficChart = new Chart(t24C, {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: "Traffic Rate (Requests per Hour)",
        data: [],
        backgroundColor: "rgba(75, 192, 192, 0.6)",
        borderColor: "rgba(75, 192, 192, 1)",
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      aspectRatio: 1,
      layout: { padding: { top: 5, bottom: 25 } },
      scales: {
        x: { title: { display: true, text: "Time (Last 24 Hours)" } },
        y: { beginAtZero: true, title: { display: true, text: "Traffic Rate" } }
      }
    }
  });
  
  function fetchAndUpdateTrafficChart() {
    fetch("/api/traffic_24h")
      .then(response => response.json())
      .then(data => {
        if (data.hours && data.traffic) {
          trafficChart.data.labels = data.hours;
          trafficChart.data.datasets[0].data = data.traffic;
          trafficChart.update();
        }
      })
      .catch(error => console.error("Error fetching traffic data:", error));
  }
  setInterval(fetchAndUpdateTrafficChart, 300000);
  fetchAndUpdateTrafficChart();
  
  // Prediction Efficiency Chart
  const pC = document.getElementById("predictiveChart").getContext("2d");
  const predictiveChart = new Chart(pC, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "Prediction Efficiency (%)",
        data: [],
        borderColor: "rgba(54, 162, 235, 1)",
        backgroundColor: "rgba(54, 162, 235, 0.2)",
        borderWidth: 1,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: "time", time: { unit: "minute" }, title: { display: true, text: "Time" } },
        y: { beginAtZero: true, suggestedMax: 100, title: { display: true, text: "Efficiency (%)" } }
      }
    }
  });
  
  function fetchAndUpdatePredictionChart() {
    fetch("/api/prediction_efficiency")
      .then(response => response.json())
      .then(data => {
        if (data.status === "success" && data.efficiency_data.length > 0) {
          predictiveChart.data.labels = data.efficiency_data.map(e => new Date(e.timestamp * 1000));
          predictiveChart.data.datasets[0].data = data.efficiency_data.map(e => e.efficiency);
          predictiveChart.update();
        }
      })
      .catch(error => console.error("Error fetching prediction efficiency:", error));
  }
  setInterval(fetchAndUpdatePredictionChart, 3000);
  fetchAndUpdatePredictionChart();
  
  // Active Connections Chart
  const acC = document.getElementById("activeconnectionChart").getContext("2d");
  const activeConnectionsChart = new Chart(acC, {
    type: "line",
    data: {
      datasets: [{
        label: "Active Connections",
        data: [],
        borderColor: "rgba(255, 99, 132, 1)",
        backgroundColor: "rgba(255, 99, 132, 0.2)",
        borderWidth: 1,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: "time", time: { unit: "second" }, title: { display: true, text: "Time" } },
        y: { beginAtZero: true, title: { display: true, text: "Connections" } }
      }
    }
  });
  
  function fetchAndUpdateConnections() {
    fetch("/api/active_connections")
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          const now = new Date();
          activeConnectionsChart.data.datasets[0].data.push({ x: now, y: data.active_connections });
          if (activeConnectionsChart.data.datasets[0].data.length > 30) {
            activeConnectionsChart.data.datasets[0].data.shift();
          }
          activeConnectionsChart.update();
        }
      })
      .catch(error => console.error("Error fetching active connections:", error));
  }
  setInterval(fetchAndUpdateConnections, 5000);
  fetchAndUpdateConnections();
  
  // Strategy
  function fetchAndUpdateStrategy() {
    const groupId = 1; // Change dynamically if needed.
    fetch(`/api/load_balancer/active_strategy/${groupId}`)
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          let strategyText = `Strategy: <b>${data.strategy_name}</b>`;
          if (data.ai_enabled) {
            strategyText += "<br><span style='color:#67FF77;'>AI Enabled</span>";
          }
          document.getElementById("strategyInfo").innerHTML = strategyText;
        } else {
          document.getElementById("strategyInfo").innerHTML = "<span style='color: red;'>No Active Strategy</span>";
        }
      })
      .catch(error => console.error("Error fetching strategy:", error));
  }
  setInterval(fetchAndUpdateStrategy, 300000);
  fetchAndUpdateStrategy();
});

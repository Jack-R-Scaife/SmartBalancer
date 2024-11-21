async function fetchAllAgentMetrics() {
    try {
        const response = await axios.get('/api/metrics/all');
        const metrics = response.data;

        metrics.forEach(metric => {
            console.log(`Agent ${metric.ip}: CPU ${metric.cpu_usage}%, Memory ${metric.memory_usage}%`);

            // Update individual agent's charts/UI
            updateAgentMetrics(metric.ip, metric.cpu_usage, metric.memory_usage);
        });
    } catch (error) {
        console.error('Error fetching metrics for all agents:', error);
    }
}

function updateAgentMetrics(agentIp, cpuUsage, memoryUsage) {
    console.log(`Updating metrics for agent ${agentIp}`);
    // Logic to update the UI for each agent
}

// Periodically fetch metrics
fetchAllAgentMetrics();
setInterval(fetchAllAgentMetrics, 5000);
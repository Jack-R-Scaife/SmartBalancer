const numberOfServers = 10; // Total number of servers
let pollInterval = 1000;
// Function to create server squares dynamically
function createServerSquares() {
    // Target the inner grid container for the squares
    const container = document.querySelector('.server-grid');
    for (let i = 1; i <= numberOfServers; i++) {
        // Create the server div
        const serverDiv = document.createElement('div');
        serverDiv.classList.add('server-square');
        serverDiv.id = `server-${i}`; // Unique ID for each square
        container.appendChild(serverDiv);
    }
}


// Function to map numeric status codes to CSS classes
function getStatusClass(statusCode) {
    switch (statusCode) {
        case 1:
            return 'healthy';
        case 2:
            return 'overloaded';
        case 3:
            return 'overloaded';
        case 4:
            return 'down';
        case 5:
            return 'idle';
        case 6:
            return 'maintenance';
        default:
            return 'down';
    }
}
// Priority order for statuses (higher index = higher priority when counts are equal)
const statusPriority = ['down', 'overloaded', 'maintenance', 'idle', 'healthy'];
// Function to update the status of the servers
function fetchServerStatus() {
    axios.get('/api/server_status')
        .then(response => {
            const servers = response.data; // Expecting an array of servers with { ip, s }

            // Initialize counters for each status
            const statusCounts = {
                healthy: 0,
                overloaded: 0,
                down: 0,
                idle: 0,
                maintenance: 0
            };

            let allIdleOrDown = true; // Track if all servers are idle or down

            servers.forEach((server, index) => {
                const serverDiv = document.getElementById(`server-${index + 1}`);

                if (serverDiv) {
                    serverDiv.classList.remove('healthy', 'overloaded', 'maintenance', 'idle', 'down');

                    const statusClass = getStatusClass(server.s);
                    serverDiv.classList.add(statusClass);

                    if (statusCounts[statusClass] !== undefined) {
                        statusCounts[statusClass]++;
                    }

                    if (server.s !== 4 && server.s !== 5) {
                        allIdleOrDown = false;
                    }
                }
            });

            // Update the monitor rectangles with the counts
            document.querySelector('.healthy .monitor-number').textContent = statusCounts.healthy;
            document.querySelector('.overloaded .monitor-number').textContent = statusCounts.overloaded;
            document.querySelector('.down .monitor-number').textContent = statusCounts.down;
            document.querySelector('.idle .monitor-number').textContent = statusCounts.idle;
            document.querySelector('.maintenance .monitor-number').textContent = statusCounts.maintenance;

            // Adjust the polling interval based on the server statuses
            pollInterval = allIdleOrDown ? 10000 : 1000;
        })
        .catch(error => {
            console.error("Error fetching server statuses:", error);
        });
}

// Function to reorder the status rectangles every 2 seconds
function reorderStatusRectangles() {
    const container = document.getElementById('serverStatusContainer');

    // Get each rectangle's current count and status for sorting
    const statusElements = Array.from(container.children).map(element => {
        const status = element.classList[0]; // The status class (e.g., 'healthy', 'overloaded')
        const count = parseInt(element.querySelector('.monitor-number').textContent, 10);
        return { status, count, element };
    });

    // Sort by count (descending), then by status priority
    statusElements.sort((a, b) => {
        if (b.count !== a.count) return b.count - a.count;
        return statusPriority.indexOf(a.status) - statusPriority.indexOf(b.status);
    });

    // Reorder the elements in the DOM based on the sorted order
    statusElements.forEach(({ element }) => {
        container.appendChild(element); // Append moves each element to the end in sorted order
    });
}

// Initial setup and polling
document.addEventListener("DOMContentLoaded", function () {
    fetchServerCount();
    createServerSquares();
    startPolling();  // Start fetching statuses at dynamic intervals
    setInterval(reorderStatusRectangles, 2000);  // Reorder rectangles every 2 seconds
});
// Recursive polling function that dynamically adjusts based on server statuses
function startPolling() {
    fetchServerStatus();
    setTimeout(startPolling, pollInterval);
}

document.addEventListener("DOMContentLoaded", function () {
    fetchServerCount();
});

function fetchServerCount() {
    fetch('/api/server_count')
    .then(response => response.json())
    .then(data => {
        document.getElementById('serverCount').textContent = data.count;
    })
    .catch(error => console.error('Error fetching server count:', error));
}


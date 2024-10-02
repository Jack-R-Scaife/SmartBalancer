const numberOfServers = 419; // Total number of servers

// Function to create server squares dynamically
function createServerSquares() {
    const container = document.getElementById('serversquares');
    for (let i = 1; i <= numberOfServers; i++) {
        // Create the server div
        const serverDiv = document.createElement('div');
        serverDiv.classList.add('server-square');
        serverDiv.id = `server-${i}`; // Assign each square a unique ID based on its index
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
            return 'critical';
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

// Function to update the status of the servers
function fetchServerStatus() {
    axios.get('/api/server_status')
        .then(response => {
            const servers = response.data; // Expecting an array of servers with { ip, s }

            servers.forEach((server, index) => {
                // Map the server to the square by index (assuming the order is consistent)
                const serverDiv = document.getElementById(`server-${index + 1}`);  // 1-based index for the div IDs

                if (serverDiv) {
                    // Reset all statuses by removing any previous class
                    serverDiv.classList.remove('healthy', 'critical', 'overloaded', 'maintenance', 'idle', 'down', 'offline');

                    // Apply the appropriate class based on the server's 's' field (now a number)
                    const statusClass = getStatusClass(server.s);
                    serverDiv.classList.add(statusClass);
                }
            });
        })
        .catch(error => {
            console.error("Error fetching server statuses:", error);
        });
}

// Create the squares when the page loads
createServerSquares();

// Fetch and update server statuses every 5 seconds
setInterval(fetchServerStatus, 5000);

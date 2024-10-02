function fetchServerStatus() {
    axios.get('/api/server_status')
        .then(response => {
            const servers = response.data;
            const container = document.getElementById('serverStatusContainer');
            container.innerHTML = ''; // Clear previous squares

            servers.forEach(server => {
                // Create a div for each server
                const serverDiv = document.createElement('div');
                serverDiv.classList.add('server-square'); // Add the square class

                // Apply the appropriate class based on the server's status
                if (server.status === 'healthy') {
                    serverDiv.classList.add('healthy');
                } else if (server.status === 'critical') {
                    serverDiv.classList.add('critical');
                } else if (server.status === 'overloaded') {
                    serverDiv.classList.add('overloaded');
                } else if (server.status === 'maintenance') {
                    serverDiv.classList.add('maintenance');
                } else if (server.status === 'idle') {
                    serverDiv.classList.add('idle');
                } else if (server.status === 'down') {
                    serverDiv.classList.add('down');
                }

                // Append the server div to the container
                container.appendChild(serverDiv);
            });
        })
        .catch(error => {
            console.error("Error fetching server statuses:", error);
        });
}

// Fetch and update server statuses every 5 seconds
setInterval(fetchServerStatus, 5000);
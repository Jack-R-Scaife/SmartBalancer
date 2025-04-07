document.addEventListener("DOMContentLoaded", () => {
    const apiUrl = '/api/servers/groups'; 

    // Function to fetch data from the API
    const fetchGroupAndServerData = async () => {
        try {
            const response = await axios.get(apiUrl);
            if (response.data.status === "success") {
                const { groups, servers } = response.data;
                cachedServers = servers;
                cachedGroups = groups;
                populateServers(servers);
                populateGroups(groups, servers);
            } else {
                console.error("API response status:", response.data.status);
            }
        } catch (error) {
            console.error("Error fetching group and server data:", error);
        }
    };

    const populateServers = (servers) => {
        const serverList = document.querySelector('#serverList'); // Updated selector
        serverList.innerHTML = ''; // Clear existing content

        servers.forEach(server => {
            const groupName = server.group ? server.group.name : "No Group";
            const listItem = document.createElement('label');
            listItem.classList.add('list-group-item');
            listItem.innerHTML = `
                <input class="form-check-input me-1" type="checkbox" value="${server.server_id}" data-type="server">
                Server ${server.server_id} (${server.server_ip}) - Group: ${groupName}
            `;
            serverList.appendChild(listItem);
        });
    };

    const populateServerList2 = () => {
        const serverList2 = document.querySelector('#serverList2'); // Target serverList2
        serverList2.innerHTML = ''; // Clear existing content

        cachedServers.forEach(server => {
            const listItem = document.createElement('label');
            listItem.classList.add('list-group-item');
            listItem.innerHTML = `
                <input class="form-check-input me-1" type="checkbox" value="${server.server_id}" name="server">
                Server ${server.server_id} - Status: ${server.group ? server.group.name : "No Group"}
            `;
            serverList2.appendChild(listItem);
        });
    };

    // Function to populate groups in the modal
    const populateGroups = (groups, servers) => {
        const groupList = document.querySelector('#groupList'); // Target the group list container
        groupList.innerHTML = ''; // Clear existing content

        groups.forEach(group => {
            // Count servers in each group
            const serverCount = servers.filter(server => server.group && server.group.group_id === group.group_id).length;

            const listItem = document.createElement('label');
            listItem.classList.add('list-group-item');
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span>
                        <input class="form-check-input me-1" type="checkbox" value="${group.group_id}" data-type="group" data-name="${group.name}">
                        ${group.name} - ${serverCount} Servers
                    </span>
                </div>
            `;

            groupList.appendChild(listItem);
        });
    };

    // Function to delete selected groups
const deleteSelectedGroups = async () => {
    // Collect all selected group checkboxes
    const selectedGroupCheckboxes = document.querySelectorAll('input[data-type="group"]:checked');
    
    // Ensure at least one group is selected
    if (selectedGroupCheckboxes.length === 0) {
        alert('Please select at least one group to delete.');
        return;
    }

    // Extract group names and IDs
    const groupNames = Array.from(selectedGroupCheckboxes).map(cb => cb.getAttribute('data-name'));
    const groupIds = Array.from(selectedGroupCheckboxes).map(cb => cb.value);

    // Confirmation alert
    const confirmDelete = confirm(`Are you sure you want to delete the following group(s): ${groupNames.join(', ')}?`);
    if (!confirmDelete) return;

    try {
        // Send a single request with all group IDs
        const response = await axios.post('/api/groups/delete', { group_ids: groupIds });

        if (response.data.status === "success") {
            alert('Selected group(s) deleted successfully.');
        } else {
            alert(`Failed to delete groups: ${response.data.message}`);
        }

        // Refresh the modal content
        fetchGroupAndServerData();
    } catch (error) {
        console.error('Error deleting group(s):', error);
        alert('An error occurred while deleting the group(s).');
    }
};

    // Add event listener to the delete button
    const deleteGroupsButton = document.getElementById('deleteGroups');
    deleteGroupsButton.addEventListener('click', deleteSelectedGroups);

    const modal = document.getElementById('addGroupModal');
    modal.addEventListener('show.bs.modal', fetchGroupAndServerData);

    // Populate serverList2 when navigating to the relevant step or section
    document.getElementById('startCreateGroup').addEventListener('click', () => {
        populateServerList2(); // Populate serverList2 when needed
    });
});
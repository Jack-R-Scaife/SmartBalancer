function checkSelection(selectId) {
    const selectElement = document.getElementById(selectId);
    if (selectElement.value === 'addGroup') {
        // Trigger the modal
        const modal = new bootstrap.Modal(document.getElementById('addGroupModal'));
        modal.show();

        // Reset selection
        selectElement.value = '';
    }
}
function toggleSubLinks(serverId) {
console.log("Configuring device for server ID:", serverId);

axios.post('/toggle_sublinks', {
    server_id: serverId
})
.then(response => {
    console.log(response.data.message);

    // Expand the sub-links in the navbar
    const subLinks = document.getElementById('serverSubLinks');
    if (subLinks) {
        subLinks.classList.add('show');
    } else {
        console.error('Sub-links element not found.');
    }
})
.catch(error => {
    console.error('There was an error!', error);
});
}

function removeServer(ipAddress) {
    fetch(`/api/servers/remove/${ipAddress}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (response.ok) {
            location.reload();  // Reload the page to update the server list
        } else {
            response.json().then(data => alert(data.message));
        }
    })
    .catch(error => console.error('Error:', error));
}
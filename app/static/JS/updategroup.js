function changeGroup(serverId) {
    const selectElement = document.getElementById(`group_${serverId}`);
    const groupId = selectElement.value;
  
    if (groupId === "manage_groups") {
      // Open the Manage Groups modal
      const addGroupModal = new bootstrap.Modal(document.getElementById('addGroupModal'));
      addGroupModal.show();
      // Reset the selection to prevent unintended actions
      selectElement.value = "";
      return;
    }
  
    if (groupId) {
      const confirmation = confirm("Are you sure you want to change this server's group?");
      if (confirmation) {
        fetch('/api/servers/update_group', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            server_id: serverId,
            group_id: groupId,
          }),
        })
        .then(response => response.json())
        .then(data => {
          if (data.status === 'success') {
            alert('Server group updated successfully');
          } else {
            alert('Failed to update server group');
          }
        })
        .catch(error => {
          console.error('Error updating server group:', error);
        });
      } else {
        // Revert the selection if the user cancels
        selectElement.selectedIndex = 0;
      }
    }
  }


  

document.addEventListener('DOMContentLoaded', () => {
    axios.get('/api/servers/groups')
      .then(response => {
        if (response.data) {
          populateDropdowns(response.data);
        }
      })
      .catch(error => {
        console.error('Error fetching server and group data:', error);
      });
  });
  
  function populateDropdowns(data) {
    const servers = data.servers;
    const groups = data.groups;
  
    servers.forEach(server => {
      const selectElement = document.getElementById(`group_${server.server_id}`);
      selectElement.innerHTML = ''; // Clear any existing options
  
      if (!server.group) {
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.text = 'Select Group';
        defaultOption.disabled = true;
        defaultOption.selected = true;
        selectElement.add(defaultOption);
      }
  
      if (server.group) {
        const groupOption = document.createElement('option');
        groupOption.value = server.group.group_id;
        groupOption.text = server.group.name;
        groupOption.selected = true;
        selectElement.add(groupOption);
      }
  
      groups.forEach(group => {
        if (!server.group || server.group.group_id !== group.group_id) {
          const option = document.createElement('option');
          option.value = group.group_id;
          option.text = group.name;
          selectElement.add(option);
        }
      });
  
      const manageGroupsOption = document.createElement('option');
      manageGroupsOption.value = 'manage_groups';
      manageGroupsOption.text = 'Manage Groups...';
      selectElement.add(manageGroupsOption);
    });
  }
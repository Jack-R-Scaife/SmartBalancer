document.getElementById('addDeviceForm').addEventListener('submit', function(event) {

    event.preventDefault();
    // Gets the IP address and dynamic grouping status from the form
    const ipAddress = document.getElementById('ipAddress').value
    const dynamicGrouping = document.getElementById('dynamicGrouping').checked;

    //Ip address is vaild
    if (!ipAddress) {
        alert('IP address cannot be empty.');
        return;  // Stop form submission if IP address is empty
    }

    if (!isValidIPv4(ipAddress) && !isValidIPv6(ipAddress)) {
        alert('Invalid IP address. Please enter a valid IPv4 or IPv6 address.');
        return;  // Stop form submission if IP is invalid
    }

    const requestData = {
        ip_address: ipAddress,
        dynamic_grouping: dynamicGrouping  
    };

    axios.post('/api/servers/link', requestData)
        .then(function(response) {
            console.log(response.data);
            alert('Server linked successfully!');
            // Optional: Close the modal after success
            let modal = bootstrap.Modal.getInstance(document.getElementById('addDeviceModal'));
            document.getElementById('addDeviceForm').reset();
        })
        .catch(function(error) {
            // Handle the error response
            console.error('Error linking server:', error);
            alert('Failed to link the server.');
        });

});
// Code adapted from https://www.geeksforgeeks.org/how-to-check-if-a-string-is-a-valid-ip-address-format-in-javascript/
function isValidIPv4(ipAddress) {
    const ipv4Regex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipv4Regex.test(ipAddress);
}

function isValidIPv6(ipAddress) {
    const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7}([0-9a-fA-F]{1,4}|:))|(([0-9a-fA-F]{1,4}:){1,7}:)|(([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4})|(([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2})|(([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3})|(([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4})|(([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5})|([0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6}))|(::([0-9a-fA-F]{1,4}:){0,7}[0-9a-fA-F]{1,4})$/;
    return ipv6Regex.test(ipAddress);
}

document.getElementById('addDeviceModal').addEventListener('hidden.bs.modal', function () {
    // Reload the page after the modal closes
    location.reload();
});
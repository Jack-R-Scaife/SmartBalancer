document.addEventListener("DOMContentLoaded", () => {
  
    // Make dependent dropdown update functions globally accessible
    window.updateRedirectTarget = function updateRedirectTarget() {
      const redirectTargetType = document.getElementById("redirectTargetType");
      if (!redirectTargetType) return;
  
      const type = redirectTargetType.value;
      if (type === "group") {
        populateDropdown("/api/get_groups", "redirectTarget", "group_id", "name", "groups", () => {
        });
      } else if (type === "server") {
        populateDropdown("/api/get_servers", "redirectTarget", "ip", "name", "servers", () => {
        });
      }
    };
  
    window.updateGeoCountry = function updateGeoCountry() {
      const geoRegion = document.getElementById("geoRegion");
      if (!geoRegion) return;
  
      const region = geoRegion.value;
      populateDropdown(`/api/get_countries?region=${region}`, "geoCountry", "code", "name", "countries", () => {
      });
    };
  
    // Reusable function to populate dropdowns via a fetch call
    function populateDropdown(apiUrl, dropdownId, valueKey, textKey, dataKey, callback) {
      // Handle optional parameters
      if (typeof dataKey === 'function') {
        callback = dataKey;
        dataKey = null;
      } else {
        callback = typeof callback !== 'undefined' ? callback : null;
      }
  
      fetch(apiUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          const dropdown = document.getElementById(dropdownId);
          if (!dropdown) return;
  
          dropdown.innerHTML = "";  // Clear existing options
  
          let items = [];
          if (Array.isArray(data)) {
            items = data;
          } else if (dataKey && data[dataKey]) {
            items = data[dataKey];
          } else {
            console.error(`Data format not recognized for ${dropdownId}`);
            return;
          }
  
          items.forEach(item => {
            const option = document.createElement("option");
            option.value = item[valueKey];
            option.textContent = item[textKey];
            dropdown.appendChild(option);
          });
  
          if (callback) callback();
        })
        .catch(error => console.error(`Error fetching ${dropdownId}:`, error));
    }
  
    // Populate load methods on initial load if the element exists
    populateDropdown("/api/get_load_methods", "loadMethod", "id", "name", () => {
    });
  
    // If any dependent dropdowns exist on page load, attach the change event listeners.
    const redirectTargetType = document.getElementById("redirectTargetType");
    if (redirectTargetType) {
      redirectTargetType.addEventListener("change", window.updateRedirectTarget);
      setTimeout(() => {
        redirectTargetType.dispatchEvent(new Event("change"));
      }, 100);
    }
  
    const geoRegion = document.getElementById("geoRegion");
    if (geoRegion) {
      geoRegion.addEventListener("change", window.updateGeoCountry);
      setTimeout(() => {
        geoRegion.dispatchEvent(new Event("change"));
      }, 100);
    }
  });
  
document.addEventListener("DOMContentLoaded", () => {
  const createRuleButton = document.getElementById("createRuleButton");
  const ruleTypeSelect = document.getElementById("ruleType");
  const ruleInputsContainer = document.getElementById("ruleInputsContainer");

  // Create Rule Button Handler remains unchanged
  if (createRuleButton) {
    createRuleButton.addEventListener("click", () => {
      const ruleData = {
        name: document.getElementById("ruleName").value.trim(),
        description: document.getElementById("ruleDescription").value.trim(),
        rule_type: ruleTypeSelect.value,
        priority: parseInt(document.getElementById("rulePriority").value) || 1,
        action: document.getElementById("ruleAction").value,
        status: document.getElementById("ruleStatus").value === "true",
        schedule: {
          days: Array.from(document.getElementById("scheduleDays").selectedOptions).map(opt => opt.value),
          start_time: document.getElementById("startTime").value || "",
          end_time: document.getElementById("endTime").value || "",
        }
      };

      // Rule Type Specific Fields
      if (ruleTypeSelect.value === "traffic") {
        ruleData.source_ip_range = document.getElementById("sourceIP")?.value.trim();
        ruleData.protocol = document.getElementById("trafficType")?.value;
        ruleData.port = document.getElementById("port")?.value || "";
        ruleData.traffic_limit = parseInt(document.getElementById("trafficLimit")?.value) || null;
        ruleData.redirect_target_type = document.getElementById("redirectTargetType")?.value || "";
        ruleData.redirect_target = document.getElementById("redirectTarget")?.value || "";
      } else if (ruleTypeSelect.value === "geo") {
        ruleData.traffic_direction = document.getElementById("geoDirection")?.value;
        ruleData.geo_region = document.getElementById("geoRegion")?.value;
        ruleData.geo_country = document.getElementById("geoCountry")?.value;
      } else if (ruleTypeSelect.value === "load") {
        ruleData.cpu_threshold = parseInt(document.getElementById("cpuThreshold")?.value) || null;
        ruleData.memory_threshold = parseInt(document.getElementById("memoryThreshold")?.value) || null;
        ruleData.applied_method = document.getElementById("loadMethod")?.value;
      }

      axios.post("/api/rules/create", ruleData)
        .then(response => alert(response.data.message))
        .catch(error => alert("Error creating rule: " + (error.response?.data?.message || error)));
    });
  }

  // Dynamic Field Loader
  function loadRuleFields() {
    const ruleType = ruleTypeSelect.value;
    ruleInputsContainer.innerHTML = "";

    const scheduleInputs = `
      <div class="row mb-3">
        <div class="col-md-4">
          <label for="scheduleDays">Days</label>
          <select id="scheduleDays" class="customselect" multiple>
            <option value="monday">Monday</option>
            <option value="tuesday">Tuesday</option>
            <option value="wednesday">Wednesday</option>
            <option value="thursday">Thursday</option>
            <option value="friday">Friday</option>
            <option value="saturday">Saturday</option>
            <option value="sunday">Sunday</option>
          </select>
        </div>
        <div class="col-md-4">
          <label for="startTime">Start Time</label>
          <input type="time" id="startTime" class="customselect">
        </div>
        <div class="col-md-4">
          <label for="endTime">End Time</label>
          <input type="time" id="endTime" class="customselect">
        </div>
      </div>`;

    switch (ruleType) {
      case "traffic":
        ruleInputsContainer.innerHTML = `
          <div class="row mb-3">
            <div class="col-md-4">
              <label for="sourceIP">Source IP Range</label>
              <input type="text" class="customselect" id="sourceIP" placeholder="e.g., 192.168.1.0/24">
            </div>
            <div class="col-md-4">
              <label for="trafficType">Traffic Type</label>
              <select id="trafficType" class="customselect">
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
              </select>
            </div>
            <div class="col-md-4">
              <label for="port">Port</label>
              <input type="text" class="customselect" id="port" placeholder="e.g., 80, 443">
            </div>
          </div>
          <div class="row mb-3">
            <div class="col-md-4">
              <label for="trafficLimit">Traffic Limit</label>
              <input type="number" class="customselect" id="trafficLimit" placeholder="Requests per minute">
            </div>
            <div class="col-md-4">
              <label for="redirectTargetType">Redirect Target Type</label>
              <select id="redirectTargetType" class="customselect">
                <option value="group">Group</option>
                <option value="server">Server</option>
              </select>
            </div>
            <div class="col-md-4">
              <label for="redirectTarget">Redirect Target</label>
              <select id="redirectTarget" class="customselect"></select>
            </div>
          </div>
          ${scheduleInputs}`;
        // After inserting the HTML, attach the event listener and trigger the update
        setTimeout(() => {
          const rtType = document.getElementById("redirectTargetType");
          if (rtType) {
            rtType.addEventListener("change", window.updateRedirectTarget);
            rtType.dispatchEvent(new Event("change"));
          }
        }, 10);
        break;

      case "geo":
        ruleInputsContainer.innerHTML = `
          <div class="row mb-3">
            <div class="col-md-4">
              <label for="geoDirection">Traffic Direction</label>
              <select id="geoDirection" class="customselect">
                <option value="incoming">Incoming</option>
                <option value="outgoing">Outgoing</option>
              </select>
            </div>
            <div class="col-md-4">
              <label for="geoRegion">Select Region</label>
              <select id="geoRegion" class="customselect">
                <option value="NA">North America</option>
                <option value="EU">Europe</option>
                <option value="AS">Asia</option>
                <option value="AF">Africa</option>
                <option value="SA">South America</option>
              </select>
            </div>
            <div class="col-md-4">
              <label for="geoCountry">Select Country</label>
              <select id="geoCountry" class="customselect"></select>
            </div>
          </div>
          ${scheduleInputs}`;
        setTimeout(() => {
          const geoRegion = document.getElementById("geoRegion");
          if (geoRegion) {
            geoRegion.addEventListener("change", window.updateGeoCountry);
            geoRegion.dispatchEvent(new Event("change"));
          }
        }, 10);
        break;
      default:
        // For rule types that don't require extra dynamic fields, include the schedule inputs
        ruleInputsContainer.innerHTML = scheduleInputs;
        break;
    }
  }

  // Initialize Rule Fields on startup and when ruleType changes
  if (ruleTypeSelect) {
    ruleTypeSelect.addEventListener("change", loadRuleFields);
    loadRuleFields(); // Initial load on page startup
  }
});

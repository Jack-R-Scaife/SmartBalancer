document.addEventListener("DOMContentLoaded", () => {
    const createRuleButton = document.getElementById("createRuleButton");
    const ruleTypeSelect = document.getElementById("ruleType");
    const ruleInputsContainer = document.getElementById("ruleInputsContainer");
  
    if (createRuleButton) {
      createRuleButton.addEventListener("click", () => {
        // Initialize rule data with general fields
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
          },
          server_groups: Array.from(document.querySelectorAll("input[type='checkbox']:checked")).map(cb => cb.value),
          redirect_target_type: document.getElementById("redirectTargetType")?.value || "",
          redirect_target: document.getElementById("redirectTarget")?.value || "",
        };
  
        // Add fields specific to Traffic-Based rules
        if (ruleTypeSelect.value === "traffic") {
          const sourceIP = document.getElementById("sourceIP")?.value.trim();
          const trafficType = document.getElementById("trafficType")?.value;
  
          if (!sourceIP || !trafficType) {
            alert("For Traffic-Based rules, Source IP Range and Traffic Type are required.");
            return;
          }
  
          ruleData.source_ip_range = sourceIP;
          ruleData.protocol = trafficType;
          ruleData.port = document.getElementById("port")?.value || "";
          ruleData.traffic_limit = parseInt(document.getElementById("trafficLimit")?.value) || null;
        }
  
        axios.post("/api/rules/create", ruleData)
          .then(response => alert(response.data.message))
          .catch(error => alert("Error creating rule: " + (error.response?.data?.message || error)));
      });
    }
  
    if (ruleTypeSelect) {
      ruleTypeSelect.addEventListener("change", () => {
        const ruleType = ruleTypeSelect.value;
        ruleInputsContainer.innerHTML = ""; // Clear previous inputs
  
        // Common schedule options for all rule types
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
                  <select id="redirectTarget" class="customselect">
                    <option value="group1">Group 1</option>
                    <option value="group2">Group 2</option>
                    <option value="server1">Server 1</option>
                    <option value="server2">Server 2</option>
                  </select>
                </div>
              </div>` + scheduleInputs;
            break;
  
          case "geo":
            ruleInputsContainer.innerHTML = `
              <div class="row mb-3">
                <div class="col-md-4">
                  <label for="geoDirection">Traffic Direction</label>
                  <select id="geoDirection" class="customselect">
                    <option value="inside">Inside</option>
                    <option value="outside">Outside</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label for="geoRegion">Region</label>
                  <select id="geoRegion" class="customselect">
                    <option value="us">US</option>
                    <option value="eu">EU</option>
                    <option value="asia">Asia</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label for="geoFilter">Filter</label>
                  <select id="geoFilter" class="customselect">
                    <option value="country">Country</option>
                    <option value="continent">Continent</option>
                  </select>
                </div>
              </div>` + scheduleInputs;
            break;
  
          case "load":
            ruleInputsContainer.innerHTML = `
              <div class="row mb-3">
                <div class="col-md-4">
                  <label for="cpuThreshold">CPU Threshold (%)</label>
                  <input type="number" id="cpuThreshold" class="customselect" min="0" max="100" placeholder="e.g., 80">
                </div>
                <div class="col-md-4">
                  <label for="memoryThreshold">Memory Threshold (%)</label>
                  <input type="number" id="memoryThreshold" class="customselect" min="0" max="100" placeholder="e.g., 70">
                </div>
                <div class="col-md-4">
                  <label for="method">Apply Method</label>
                  <select id="method" class="customselect">
                    <option value="round_robin">Round Robin</option>
                    <option value="weighted_round_robin">Weighted Round Robin</option>
                    <option value="least_connections">Least Connections</option>
                  </select>
                </div>
              </div>` + scheduleInputs;
            break;
  
          case "custom":
            ruleInputsContainer.innerHTML = `
              <div class="row mb-3">
                <div class="col-md-12">
                  <label for="customRuleJSON">Custom Rule (JSON)</label>
                  <textarea id="customRuleJSON" class="customselect" rows="6" placeholder="Enter custom rule in JSON format"></textarea>
                </div>
              </div>` + scheduleInputs;
            break;
  
          default:
            ruleInputsContainer.innerHTML = ""; // Clear for unrecognized types
            break;
        }
      });
  
      // Trigger change to show the initial form based on default rule type
      ruleTypeSelect.dispatchEvent(new Event("change"));
    }
  });
  
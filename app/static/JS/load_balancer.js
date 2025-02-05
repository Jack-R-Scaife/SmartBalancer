document.addEventListener("DOMContentLoaded", async function () {
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Get all the UI elements
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  const staticMethodCheckbox   = document.getElementById("staticMethod");
  const dynamicMethodCheckbox  = document.getElementById("dynamicMethod");
  const customCheckbox         = document.getElementById("Custom");
  const predictiveAICheckbox   = document.getElementById("predictiveAI");
  let userStrategyOrder = []; 
  const resourceCheckBoxes = {
    cpu: document.getElementById("cpuUsage"),
    memory: document.getElementById("memoryUsage"),
    disk: document.getElementById("diskUsage"),
    leastConnections: document.getElementById("leastConnectionsResource"),
  };

  const resourceWeightsSelects = {
    cpu: document.getElementById("cpuUsageWeight"),
    memory: document.getElementById("memoryUsageWeight"),
    disk: document.getElementById("diskUsageWeight"),
    leastConnections: document.getElementById("leastConnectionsWeight"),
  };

  const failoverPriority1 = document.getElementById("failoverPriority1");
  const failoverPriority2 = document.getElementById("failoverPriority2");

  // Strategy checkboxes in the HTML
  const RoundRobin         = document.getElementById("RoundRobin");
  const WeightedRoundRobin = document.getElementById("WeightedRoundRobin");
  const LeastConnections   = document.getElementById("LeastConnections");
  const LeastResponseTime  = document.getElementById("LeastResponseTime");
  const ResourceBased      = document.getElementById("Resource-Based");

  const allStrategies = [
    RoundRobin,
    WeightedRoundRobin,
    LeastConnections,
    LeastResponseTime,
    ResourceBased
  ];

  // A corrections map for pretty names
  const nameCorrections = {
    "RoundRobin": "Round Robin",
    "WeightedRoundRobin": "Weighted Round Robin",
    "LeastConnections": "Least Connections",
    "LeastResponseTime": "Least Response Time",
    "Resource-Based": "Resource-Based"
  };

  const applyBtn = document.getElementById("tab2button");
  let loadingFromStorage = false; // flag to prevent unwanted resets

  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Initialization: disable everything and load config
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  disableAll();
  if (!loadFromLocalStorage()) {
    await loadCurrentConfiguration();
  }

  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Functions for UI state management
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  function disableAll() {
    // Disable and uncheck strategies
    allStrategies.forEach(chk => {
      chk.disabled = true;
      chk.checked = false;
    });
    // Disable and uncheck resource checkboxes
    Object.values(resourceCheckBoxes).forEach(cb => {
      cb.disabled = true;
      cb.checked = false;
    });
    // Disable and reset resource weights
    Object.values(resourceWeightsSelects).forEach(sel => {
      sel.disabled = true;
      sel.value = "0";
    });
    // Disable predictive AI
    predictiveAICheckbox.disabled = true;
    predictiveAICheckbox.checked = false;
    // Reset failover selects
    failoverPriority1.innerHTML = `<option>No strategies selected</option>`;
    failoverPriority2.innerHTML = `<option>No strategies selected</option>`;
  }

  function enableAllCheckboxes() {
    console.log("No settings found, enabling method checkboxes.");
    staticMethodCheckbox.disabled = false;
    dynamicMethodCheckbox.disabled = false;
    customCheckbox.disabled = false;
    // Keep strategies and resources disabled
    allStrategies.forEach(chk => {
      chk.disabled = true;
      chk.checked = false;
    });
    Object.values(resourceCheckBoxes).forEach(cb => {
      cb.disabled = true;
      cb.checked = false;
    });
    Object.values(resourceWeightsSelects).forEach(sel => {
      sel.disabled = true;
      sel.value = "0";
    });
    predictiveAICheckbox.disabled = true;
    predictiveAICheckbox.checked = false;
    // Update failover dropdowns to reflect no strategies
    failoverPriority1.innerHTML = `<option>No strategies selected</option>`;
    failoverPriority2.innerHTML = `<option>No strategies selected</option>`;
  }
  function onDropdownChange() {
    // Update the stored ordering based on the dropdowns.
    // Assume the dropdowns are now the source of truth.
    userStrategyOrder = [];
    if (failoverPriority1.value && failoverPriority1.value !== "No strategies selected") {
      userStrategyOrder.push(failoverPriority1.value);
    }
    if (failoverPriority2.value && failoverPriority2.value !== "No strategies selected" && failoverPriority2.value !== failoverPriority1.value) {
      userStrategyOrder.push(failoverPriority2.value);
    }
  }
  
  failoverPriority1.addEventListener("change", onDropdownChange);
  failoverPriority2.addEventListener("change", onDropdownChange);
  // This function updates dropdowns based solely on currently checked strategies.

  function updateFailoverPriority() {
    // Get stored strategies from localStorage
    const stored = JSON.parse(localStorage.getItem("myLBConfig") || "{}");
    const storedOrder = stored.strategies || [];
    
    // Get currently active strategies
    const activeStrategies = allStrategies
      .filter(chk => chk.checked)
      .map(chk => nameCorrections[chk.id] || chk.id);
  
    // Preserve stored order for active strategies
    const orderedStrategies = storedOrder.filter(s => activeStrategies.includes(s));
    // Add any new strategies not in stored order
    const newStrategies = activeStrategies.filter(s => !storedOrder.includes(s));
    const finalStrategies = [...orderedStrategies, ...newStrategies];
  
    // Preserve current selections
    const originalPriority1 = failoverPriority1.value;
    const originalPriority2 = failoverPriority2.value;
  
    // Rebuild options using final order
    failoverPriority1.innerHTML = finalStrategies.map(s => 
      `<option value="${s}">${s}</option>`
    ).join('');
    failoverPriority2.innerHTML = finalStrategies.map(s => 
      `<option value="${s}">${s}</option>`
    ).join('');
  
    // Restore selections
    failoverPriority1.value = originalPriority1;
    failoverPriority2.value = originalPriority2;
  
    // Validate and fallback if needed
    if (!finalStrategies.includes(failoverPriority1.value) && finalStrategies.length > 0) {
      failoverPriority1.value = finalStrategies[0];
    }
    if ((!finalStrategies.includes(failoverPriority2.value) || 
         failoverPriority2.value === failoverPriority1.value) && 
        finalStrategies.length > 1) {
      failoverPriority2.value = finalStrategies[1];
    }
  
    // Handle empty state
    if (finalStrategies.length === 0) {
      failoverPriority1.innerHTML = `<option>No strategies selected</option>`;
      failoverPriority2.innerHTML = `<option>No strategies selected</option>`;
    }
  }

  function updatePredictiveAICheckbox() {
    const anyChecked = allStrategies.some(chk => chk.checked);
    predictiveAICheckbox.disabled = !anyChecked;
    if (!anyChecked) {
      predictiveAICheckbox.checked = false;
    }
  }

  // This function toggles which strategy checkboxes are enabled based on method selections.
  function handleMethodChange() {
    if (loadingFromStorage) return; // Skip during load
  
    if (customCheckbox.checked) {
      toggleCheckboxes(allStrategies, true);
    } else {
      toggleCheckboxes([RoundRobin, WeightedRoundRobin], staticMethodCheckbox.checked);
      toggleCheckboxes([LeastConnections, LeastResponseTime, ResourceBased], dynamicMethodCheckbox.checked);
    }
    toggleResourceUsage(ResourceBased.checked);
    updatePredictiveAICheckbox();
    updateFailoverPriority();
    predictiveAICheckbox.disabled = !allStrategies.some(chk => chk.checked);
    if (!predictiveAICheckbox.disabled) {
      predictiveAICheckbox.checked = localStorage.getItem("myLBConfig") 
        ? JSON.parse(localStorage.getItem("myLBConfig")).ai_enabled 
        : false;
    }
  }
  

  function toggleCheckboxes(list, enable) {
    list.forEach(chk => {
      chk.disabled = !enable;
      // Only uncheck if disabling and not loading from storage
      if (!enable && !loadingFromStorage) {
        chk.checked = false;
      }
    });
  }

  function toggleResourceUsage(enable) {
    for (const [k, cb] of Object.entries(resourceCheckBoxes)) {
      cb.disabled = !enable;
      if (!enable && !loadingFromStorage) cb.checked = false;
    }
    for (const [k, sel] of Object.entries(resourceWeightsSelects)) {
      sel.disabled = !enable;
      if (!enable && !loadingFromStorage) sel.value = "0";
    }
  }
  function updateServerWeightsEnabled() {
    const serverWeightsDiv = document.getElementById("serverWeights");
    if (!serverWeightsDiv) return;
    // Find all <select> elements with class "customselect" within the serverWeights div.
    const selects = serverWeightsDiv.querySelectorAll("select.customselect");
    // Enable only if both Static Method and Weighted Round Robin are active.
    const staticMethodCheckbox = document.getElementById("staticMethod");
    const WeightedRoundRobin = document.getElementById("WeightedRoundRobin");
    const enable = staticMethodCheckbox.checked && WeightedRoundRobin.checked;
    selects.forEach(sel => {
       sel.disabled = !enable;
    });
  }
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Local Storage & Server Sync Functions
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  async function loadCurrentConfiguration() {
    try {
      const groupId = getGroupId();
      const settingsResp = await axios.get(`/api/load_balancer/settings/${groupId}`);
      const settingsData = settingsResp.data;
      if (settingsData.status !== "success" || !settingsData.active_strategy) {
        console.warn("No settings found. Enabling UI for a new group.");
        enableAllCheckboxes();
        return;
      }

      let resourceWeightsData = {};
      if (settingsData.active_strategy === "Resource-Based") {
        const wResp = await axios.get(`/api/load_balancer/resource_weights/${groupId}`);
        if (wResp.data.status === "success") {
          resourceWeightsData = wResp.data.weights;
        }
      }

      // Build payload from server settings.
      const payload = {
        group_id: "" + groupId,
        methods: [],
        strategies: [],
        weights: {},
        ai_enabled: !!settingsData.ai_enabled
      };

      const dynamicSet = ["LeastConnections", "LeastResponseTime", "Resource-Based"];
      const staticSet  = ["RoundRobin", "WeightedRoundRobin"];
      if (dynamicSet.includes(settingsData.active_strategy)) payload.methods.push("dynamic");
      if (staticSet.includes(settingsData.active_strategy))  payload.methods.push("static");

      if (Array.isArray(settingsData.failover_priority) && settingsData.failover_priority.length > 0) {
        payload.strategies = settingsData.failover_priority.map(s => s.trim());
      } else if (settingsData.active_strategy) {
        payload.strategies = [settingsData.active_strategy.trim()];
      }

      // Adjust resource weight keys if needed.
      if (typeof resourceWeightsData.connections !== "undefined") {
        resourceWeightsData.leastConnections = resourceWeightsData.connections;
        delete resourceWeightsData.connections;
      }
      for (const [k, v] of Object.entries(resourceWeightsData)) {
        payload.weights[k] = "" + v;
      }
      payload.ai_enabled = !!settingsData.ai_enabled;

      localStorage.setItem("myLBConfig", JSON.stringify(payload));

      // Load from localStorage to update the UI.
      loadFromLocalStorage();
      handleMethodChange();
    } catch (err) {
      console.error("Error loading config from server:", err);
    }
  }

  function loadFromLocalStorage() {
    const raw = localStorage.getItem("myLBConfig");
    if (!raw) return false;
    try {
      loadingFromStorage = true;
      // First, disable all UI elements.
      disableAll();
      const stored = JSON.parse(raw);
      
      // Restore method selections based on stored strategies.
      const hasStatic = stored.strategies.some(s => 
        ["Round Robin", "Weighted Round Robin"].includes(s)
      );
      const hasDynamic = stored.strategies.some(s =>
        ["Least Connections", "Least Response Time", "Resource-Based"].includes(s)
      );
      
      document.getElementById("staticMethod").checked = hasStatic;
      document.getElementById("dynamicMethod").checked = hasDynamic;
      document.getElementById("Custom").checked = stored.methods.includes("custom");
      
      // Restore strategy checkboxes.
      const nameCorrections = {
        "RoundRobin": "Round Robin",
        "WeightedRoundRobin": "Weighted Round Robin",
        "LeastConnections": "Least Connections",
        "LeastResponseTime": "Least Response Time",
        "Resource-Based": "Resource-Based"
      };
      stored.strategies.forEach(displayName => {
        const strategyId = Object.entries(nameCorrections)
          .find(([id, name]) => name === displayName)?.[0] || displayName.replace(/ /g, '');
        const chk = document.getElementById(strategyId);
        if (chk) chk.checked = true;
      });
      
      // Restore resource weights.
      const resourceCheckBoxes = {
        cpu: document.getElementById("cpuUsage"),
        memory: document.getElementById("memoryUsage"),
        disk: document.getElementById("diskUsage"),
        leastConnections: document.getElementById("leastConnectionsResource")
      };
      const resourceWeightsSelects = {
        cpu: document.getElementById("cpuUsageWeight"),
        memory: document.getElementById("memoryUsageWeight"),
        disk: document.getElementById("diskUsageWeight"),
        leastConnections: document.getElementById("leastConnectionsWeight")
      };
      Object.entries(stored.weights).forEach(([key, val]) => {
        // Adjust key name if needed.
        const resourceKey = key === "connections" ? "leastConnections" : key;
        if (resourceCheckBoxes[resourceKey]) {
          resourceCheckBoxes[resourceKey].checked = true;
          resourceWeightsSelects[resourceKey].value = val;
        }
      });
      
      // ── NEW: Restore server weights if they exist ──
      if (stored.server_weights) {
        const serverWeightsDiv = document.getElementById("serverWeights");
        if (serverWeightsDiv) {
          Object.entries(stored.server_weights).forEach(([serverId, weightVal]) => {
            const sel = document.getElementById(`weight_${serverId}`);
            if (sel) {
              sel.value = weightVal;
            }
          });
        }
      }
      
      // Update failover priorities if needed.
      const failoverPriority1 = document.getElementById("failoverPriority1");
      const failoverPriority2 = document.getElementById("failoverPriority2");
      failoverPriority1.value = stored.strategies[0] || "";
      failoverPriority2.value = stored.strategies[1] || "";
      
      // Update the rest of the UI.
      handleMethodChange();
      return true;
    } catch (err) {
      console.error("Error parsing localStorage:", err);
      return false;
    } finally {
      loadingFromStorage = false;
    }
  }
  


  

  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Build payload from UI to send/save changes.
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  function buildPayloadFromUI() {
    const groupId = getGroupId();
    const methods = [];
    if (document.getElementById("staticMethod").checked) methods.push("static");
    if (document.getElementById("dynamicMethod").checked) methods.push("dynamic");
    if (document.getElementById("Custom").checked) methods.push("custom");
  
    // Validate at least one method is selected.
    if (methods.length === 0) {
      alert("Please select at least one method.");
      return null;
    }
  
    // Capture both failover priorities from the dropdowns.
    const strategies = [];
    const failoverPriority1 = document.getElementById("failoverPriority1");
    const failoverPriority2 = document.getElementById("failoverPriority2");
    if (failoverPriority1.value && failoverPriority1.value !== "No strategies selected") {
      strategies.push(failoverPriority1.value);
    }
    if (failoverPriority2.value && failoverPriority2.value !== "No strategies selected") {
      strategies.push(failoverPriority2.value);
    }
  
    // Capture resource weights.
    const weights = {};
    const resourceCheckBoxes = {
      cpu: document.getElementById("cpuUsage"),
      memory: document.getElementById("memoryUsage"),
      disk: document.getElementById("diskUsage"),
      leastConnections: document.getElementById("leastConnectionsResource")
    };
    const resourceWeightsSelects = {
      cpu: document.getElementById("cpuUsageWeight"),
      memory: document.getElementById("memoryUsageWeight"),
      disk: document.getElementById("diskUsageWeight"),
      leastConnections: document.getElementById("leastConnectionsWeight")
    };
    Object.entries(resourceCheckBoxes).forEach(([key, checkbox]) => {
      if (checkbox.checked) {
        const weightKey = key === "leastConnections" ? "connections" : key;
        weights[weightKey] = resourceWeightsSelects[key].value;
      }
    });
  
    // ── NEW: Capture server weights if Weighted Round Robin is active ──
    let serverWeights = {};
    if (document.getElementById("staticMethod").checked && document.getElementById("WeightedRoundRobin").checked) {
      const serverWeightsDiv = document.getElementById("serverWeights");
      if (serverWeightsDiv) {
        const selects = serverWeightsDiv.querySelectorAll("select.customselect");
        selects.forEach(select => {
          // Expected ID format: "weight_{serverId}"
          const serverId = select.id.replace("weight_", "");
          serverWeights[serverId] = select.value;
        });
      }
    }
  
    return {
      group_id: groupId,
      methods,
      strategies: strategies.length > 0 ? strategies : ["Resource-Based"], // fallback
      weights,
      server_weights: serverWeights, // include server weights in payload
      ai_enabled: document.getElementById("predictiveAI").checked
    };
  }
  
  

  function getGroupId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get("group_id") || "1";
  }

  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Event listeners and final initialization
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  applyBtn.addEventListener("click", () => {
    if (!validateWeights()) return;
    const payload = buildPayloadFromUI();
    if (!payload) return;
  
    // Fix: Initialize as Set instead of array
    const requiredMethods = new Set();
    
    // Check strategy types and add required methods
    payload.strategies.forEach(s => {
      const strategyId = s.replace(/ /g, '');
      if (["RoundRobin", "WeightedRoundRobin"].includes(strategyId)) {
        requiredMethods.add("static");
      } else if (["LeastConnections", "LeastResponseTime", "Resource-Based"].includes(strategyId)) {
        requiredMethods.add("dynamic");
      }
    });
  
    // Convert Set to array for easier manipulation
    const requiredMethodsArray = Array.from(requiredMethods);
    
    // Check if all required methods are enabled
    const missingMethods = requiredMethodsArray.filter(m => !payload.methods.includes(m));
    if (missingMethods.length > 0) {
      alert(`Please enable the ${missingMethods.join("/")} method(s) for your selected strategies.`);
      return;
    }
  
    // Save and reload
    localStorage.setItem("myLBConfig", JSON.stringify(payload));
  axios.post("/api/load_balancer/set_strategy", payload)
    .then(resp => {
      if (resp.data.status === "success") {
        alert("Strategy applied successfully.");
        // Force complete UI refresh
        disableAll();
        loadFromLocalStorage();
        handleMethodChange();
      }
    })
    .catch(err => {
      console.error("Error applying strategy:", err);
    });
});

  staticMethodCheckbox.addEventListener("change", handleMethodChange);
  dynamicMethodCheckbox.addEventListener("change", handleMethodChange);
  customCheckbox.addEventListener("change", handleMethodChange);
  allStrategies.forEach(chk => {
    chk.addEventListener("change", handleMethodChange);
  });
  Object.keys(resourceCheckBoxes).forEach(k => {
    resourceCheckBoxes[k].addEventListener("change", () => {
      const sel = resourceWeightsSelects[k];
      sel.disabled = !resourceCheckBoxes[k].checked;
      if (!resourceCheckBoxes[k].checked && !loadingFromStorage) {
        sel.value = "0";
      }
    });
  });
  // Final UI update
  handleMethodChange();
  
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  // Validate resource weights before applying changes.
  // ––––––––––––––––––––––––––––––––––––––––––––––––––––––
  function validateWeights() {
    if (!ResourceBased.checked) return true;
    let total = 0;
    Object.entries(resourceCheckBoxes).forEach(([key, cb]) => {
      if (cb.checked) {
        const wVal = parseInt(resourceWeightsSelects[key].value, 10);
        if (wVal <= 0) {
          alert(`Weight for ${key.replace(/([A-Z])/g, ' $1')} must be > 0`);
          return false;
        }
        total += wVal;
      }
    });
    if (total <= 0) {
      alert("At least one resource weight must be > 0");
      return false;
    }
    return true;
  }
});

document.addEventListener("DOMContentLoaded", async function () {
  const staticMethodCheckbox   = document.getElementById("staticMethod");
  const dynamicMethodCheckbox  = document.getElementById("dynamicMethod");
  const customCheckbox         = document.getElementById("Custom");
  const predictiveAICheckbox   = document.getElementById("predictiveAI");

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

  const applyBtn = document.getElementById("tab2button");

  // This flag prevents wiping out resource weights if we’re just loading from localStorage
  let loadingFromStorage = false;

  disableAll();

  // If localStorage does NOT have config, we load from server
  if (!loadFromLocalStorage()) {
    await loadCurrentConfiguration();
  }

  function disableAll() {
    // Clear and disable all strategy checkboxes
    allStrategies.forEach(chk => {
      chk.disabled = true;
      chk.checked = false;
    });
    // Clear resource usage
    Object.values(resourceCheckBoxes).forEach(cb => {
      cb.disabled = true;
      cb.checked = false;
    });
    // Reset resource weights
    Object.values(resourceWeightsSelects).forEach(sel => {
      sel.disabled = true;
      sel.value = "0";
    });
    // Turn off AI
    predictiveAICheckbox.disabled = true;
    predictiveAICheckbox.checked = false;

    // Clear priority <selects>
    failoverPriority1.innerHTML = `<option>No strategies selected</option>`;
    failoverPriority2.innerHTML = `<option>No strategies selected</option>`;
  }

  // loadCurrentConfiguration() from server if no localStorage 

  async function loadCurrentConfiguration() {
    try {
      const groupId = getGroupId();
      const settingsResp = await axios.get(`/api/load_balancer/settings/${groupId}`);
      const settingsData = settingsResp.data;

      if (settingsData.status !== "success") {
        console.warn("No settings or error in response:", settingsData.message);
        return;
      }

      // If Resource-Based is active, fetch resource-based weights
      let resourceWeightsData = {};
      if (settingsData.active_strategy === "Resource-Based") {
        const wResp = await axios.get(`/api/load_balancer/resource_weights/${groupId}`);
        if (wResp.data.status === "success") {
          resourceWeightsData = wResp.data.weights; // e.g. {cpu: 40, memory: 30, disk: 20, connections: 10}
        }
      }
      const payload = {
        group_id: ""+groupId,
        methods: [],
        strategies: [],
        weights: {},
        ai_enabled: !!settingsData.ai_enabled
      };

      const dynamicSet = ["LeastConnections","LeastResponseTime","Resource-Based"];
      const staticSet  = ["RoundRobin","WeightedRoundRobin"];

      if (dynamicSet.includes(settingsData.active_strategy)) {
        payload.methods.push("dynamic");
      }
      if (staticSet.includes(settingsData.active_strategy)) {
        payload.methods.push("static");
      }
      if (Array.isArray(settingsData.failover_priority) && settingsData.failover_priority.length > 0) {
        // Trim them just in case
        payload.strategies = settingsData.failover_priority.map(s => s.trim());
      } else if (settingsData.active_strategy) {
        payload.strategies = [settingsData.active_strategy.trim()];
      }
      // Map resource "connections" => "leastConnections"
      if (typeof resourceWeightsData.connections !== "undefined") {
        resourceWeightsData.leastConnections = resourceWeightsData.connections;
        delete resourceWeightsData.connections;
      }
      // Convert numeric to string
      for (const [k, v] of Object.entries(resourceWeightsData)) {
        payload.weights[k] = ""+v;
      }
      payload.ai_enabled = !!settingsData.ai_enabled;

      // Save that to localStorage
      localStorage.setItem("myLBConfig", JSON.stringify(payload));

      // Then load from localStorage
      loadFromLocalStorage();

    } catch (err) {
      console.error("Error loading config from server:", err);
    }
  }
  // loadFromLocalStorage() -> returns true if found
  function loadFromLocalStorage() {
    const raw = localStorage.getItem("myLBConfig");
    if (!raw) return false;

    try {
      loadingFromStorage = true;
      disableAll();  

      const stored = JSON.parse(raw);
      console.log("Loaded from localStorage:", stored);

      // (A) Mark "methods"
      if (Array.isArray(stored.methods)) {
        if (stored.methods.includes("dynamic")) dynamicMethodCheckbox.checked = true;
        if (stored.methods.includes("static"))  staticMethodCheckbox.checked = true;
        if (stored.methods.includes("custom"))  customCheckbox.checked = true;
      }
      handleMethodChange();

      if (Array.isArray(stored.strategies)) {
        for (let s of stored.strategies) {
          const id = s.replace(/ /g,'');
          const chk = document.getElementById(id);
          if (chk) {
            chk.checked = true;
          }
        }
      }
      if (Array.isArray(stored.strategies) && stored.strategies.length > 0) {
        buildFailoverSelects(stored.strategies); 
      } else {
        failoverPriority1.innerHTML = `<option>No strategies selected</option>`;
        failoverPriority2.innerHTML = `<option>No strategies selected</option>`;
      }

      // (C) Resource usage
      if (stored.weights) {
        for (const [k, val] of Object.entries(stored.weights)) {
          const cb  = resourceCheckBoxes[k];
          const sel = resourceWeightsSelects[k];
          if (cb && sel) {
            cb.checked = true;
            sel.value = val;
          }
        }
      }

      predictiveAICheckbox.checked = !!stored.ai_enabled;
      // Fire handleMethodChange again so resource usage toggles are correct
      handleMethodChange();

      console.log("UI updated from localStorage config.");
      return true;

    } catch (err) {
      console.error("Error parsing localStorage config:", err);
      return false;
    } finally {
      loadingFromStorage = false;
    }
  }
  // buildFailoverSelects(strArray) in the exact localStorage order
  function buildFailoverSelects(strArray) {
    // e.g. strArray = [ "Resource-Based", "Round Robin" ]
    failoverPriority1.innerHTML = "";
    failoverPriority2.innerHTML = "";

    strArray.forEach(s => {
      failoverPriority1.innerHTML += `<option value="${s}">${s}</option>`;
      failoverPriority2.innerHTML += `<option value="${s}">${s}</option>`;
    });

    // Now set the .value to the first in the array for Priority1, second for Priority2
    // If we have at least 1
    if (strArray[0]) {
      failoverPriority1.value = strArray[0];
    }
    // If we have at least 2
    if (strArray[1]) {
      failoverPriority2.value = strArray[1];
    }
  }

  //  handleMethodChange() toggles “static/dynamic” checkboxes, resource usage, etc.
  function handleMethodChange() {
    if (customCheckbox.checked) {
      toggleCheckboxes(allStrategies, true);
    } else {
      // If static => enable RoundRobin, WeightedRoundRobin
      toggleCheckboxes([RoundRobin, WeightedRoundRobin], staticMethodCheckbox.checked);
      // If dynamic => enable dynamic ones
      toggleCheckboxes([LeastConnections, LeastResponseTime, ResourceBased], dynamicMethodCheckbox.checked);
    }

    // Resource usage only relevant if ResourceBased is checked
    const resourceBasedChecked = ResourceBased.checked;
    toggleResourceUsage(resourceBasedChecked);

    updatePredictiveAICheckbox();
  }

  function toggleCheckboxes(list, enable) {
    list.forEach(chk => {
      chk.disabled = !enable;
      if (!enable) {
        chk.checked = false;
      }
    });
  }

  function toggleResourceUsage(enable) {
    for (const [k, cb] of Object.entries(resourceCheckBoxes)) {
      cb.disabled = !enable;
      if (!enable && !loadingFromStorage) {
        cb.checked = false;
      }
    }
    for (const [k, sel] of Object.entries(resourceWeightsSelects)) {
      sel.disabled = !enable;
      if (!enable && !loadingFromStorage) {
        sel.value = "0";
      }
    }
  }
  //  updatePredictiveAICheckbox() 
  function updatePredictiveAICheckbox() {
    const anyChecked = allStrategies.some(chk => chk.checked);
    predictiveAICheckbox.disabled = !anyChecked;
    if (!anyChecked) {
      predictiveAICheckbox.checked = false;
    }
  }
  // validateWeights() before “Apply Changes” 
  function validateWeights() {
    if (!ResourceBased.checked) return true;

    // If Resource-Based is checked => all checked resources must have weight>0, no duplicates
    const used = [];
    for (const [k, cb] of Object.entries(resourceCheckBoxes)) {
      if (cb.checked) {
        const wVal = parseInt(resourceWeightsSelects[k].value, 10);
        if (wVal <= 0) {
          alert(`Please assign a weight > 0 for "${k.toUpperCase()}"`);
          return false;
        }
        if (used.includes(wVal)) {
          alert(`Two resources cannot share the same weight (${wVal})`);
          return false;
        }
        used.push(wVal);
      }
    }
    return true;
  }

  function buildPayloadFromUI() {
    const groupId = getGroupId();

    const methods = [];
    if (staticMethodCheckbox.checked)  methods.push("static");
    if (dynamicMethodCheckbox.checked) methods.push("dynamic");
    if (customCheckbox.checked)        methods.push("custom");


    const raw = localStorage.getItem("myLBConfig") || "{}";
    const stored = JSON.parse(raw);
    let finalStrats = Array.isArray(stored.strategies) ? [...stored.strategies] : [];

    // Resource weights from the UI
    const chosenWeights = {};
    for (const [k,cb] of Object.entries(resourceCheckBoxes)) {
      if (cb.checked) {
        chosenWeights[k] = resourceWeightsSelects[k].value;
      }
    }

    return {
      group_id: groupId,
      methods,
      strategies: finalStrats,
      weights: chosenWeights,
      ai_enabled: predictiveAICheckbox.checked
    };
  }

  // getGroupId() Helper
  function getGroupId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get("group_id") || "1";
  }

  //  “Apply Changes” => localStorage + POST
  applyBtn.addEventListener("click", () => {
    // Validate resource-based
    if (!validateWeights()) return;

    // Build final payload from UI
    const payload = buildPayloadFromUI();

    // Save to localStorage so next reload matches
    localStorage.setItem("myLBConfig", JSON.stringify(payload));
    console.log("Saved to localStorage:", payload);

    // POST to server
    axios.post("/api/load_balancer/set_strategy", payload)
      .then(resp => {
        if (resp.data.status === "success") {
          alert(resp.data.message || "Strategy applied successfully on server.");
        } else {
          alert(resp.data.message || "An error occurred while applying strategy on server.");
        }
      })
      .catch(err => {
        console.error("Error applying strategy on server:", err);
        alert(`Failed to apply strategy on server: ${err.response?.data?.message || err.message}`);
      });
  });
  //  Attach event listeners for checkboxes, resource usage, etc.
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

});

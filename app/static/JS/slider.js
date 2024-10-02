

document.addEventListener('DOMContentLoaded', function() {
  function initializeSlider(sliderId, valueDisplayId, unit = '') {
      const slider = document.getElementById(sliderId);
      const valueDisplay = document.getElementById(valueDisplayId);

      // Check if both slider and valueDisplay exist
      if (slider && valueDisplay) {
          slider.addEventListener('input', function() {
              const percentage = (this.value - this.min) / (this.max - this.min) * 100;
              this.style.background = `linear-gradient(to right, rgb(255, 117, 117) ${percentage}%, rgb(255, 255, 255) ${percentage}%)`;
              valueDisplay.textContent = this.value + unit;
          });
      } else {
          console.log(`Slider or value display not found for: ${sliderId}. Skipping initialization.`);
      }
  }

  // Initialize sliders only if they exist
  initializeSlider('threadPoolSizeSlider', 'threadPoolSizeValue', '%');
  initializeSlider('baseFrequencySlider', 'baseFrequencyValue', ' MHz');
  initializeSlider('maxFrequencySlider', 'maxFrequencyValue', ' ms');
  initializeSlider('maxThreadsSlider', 'maxThreadsValue', ' Threads');
  initializeSlider('cpuUtilSlider', 'cpuUtilValue', '%');
  initializeSlider('maxConnections', 'maxConnectionsValue','%');
  initializeSlider('networkThrottle', 'networkthrottleValue', '%');
});

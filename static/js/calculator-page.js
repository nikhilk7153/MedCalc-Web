(function (global) {
  function initCalculatorPage(config) {
    const form = document.getElementById(config.formId);
    if (!form) {
      console.warn(`[calculator] Form with id "${config.formId}" not found.`);
      return;
    }

    const submitButton = document.getElementById(config.submitButtonId);
    const errorBox = document.getElementById(config.errorBoxId || "error-message");
    const errorText = document.getElementById(config.errorTextId || "error-text");

    const baseEndpoint = (() => {
      if (config.endpoint) return config.endpoint;
      if (!config.slug) return "";
      const base = (config.apiBase || "").replace(/\/$/, "");
      const slugSegment = `/api/calculators/${config.slug}`;
      return `${base}${slugSegment}`;
    })();

    if (!baseEndpoint && typeof config.getEndpoint !== "function") {
      console.warn("[calculator] No endpoint provided for calculator form.");
      return;
    }

    const setButtonState = (isLoading) => {
      if (!submitButton) return;
      submitButton.disabled = isLoading;
      const label = config.buttonLabel || submitButton.dataset.label || "Calculate";
      submitButton.textContent = isLoading ? `${label}…` : label;
      submitButton.classList.toggle("opacity-70", isLoading);
    };

    const showError = (message) => {
      if (!errorBox || !errorText) return;
      errorText.textContent = message;
      errorBox.classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const hideError = () => {
      if (!errorBox) return;
      errorBox.classList.add("hidden");
    };

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideError();
      setButtonState(true);

      let payload;
      try {
        payload = config.collectPayload();
      } catch (err) {
        setButtonState(false);
        showError(err.message || "Please review the highlighted inputs.");
        return;
      }

      try {
        let requestEndpoint = baseEndpoint;
        if (typeof config.getEndpoint === "function") {
          requestEndpoint = config.getEndpoint(payload, baseEndpoint);
        }

        if (!requestEndpoint) {
          throw new Error("Calculator endpoint is not configured.");
        }

        const response = await fetch(requestEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorPayload = await response.json().catch(() => ({}));
          throw new Error(errorPayload.detail || "Unable to complete the calculation.");
        }

        const result = await response.json();
        if (typeof config.onResult === "function") {
          config.onResult(result);
        }
      } catch (err) {
        showError(err.message || "Something went wrong. Please try again.");
      } finally {
        setButtonState(false);
      }
    });
  }

  global.CalculatorPage = {
    init: initCalculatorPage,
  };
})(window);


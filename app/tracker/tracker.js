(function () {
  console.log("🛰️ Bybarter Tracker initialized...");

  // 🚀 AUTOMATIC API KEY EXTRACTION
  // Find the exact script tag loading this file and read its data-api-key attribute
  const currentScript = document.querySelector('script[src*="tracker.js"]');
  const companyApiKey = currentScript ? currentScript.getAttribute('data-api-key') : null;

  if (!companyApiKey) {
    console.error("❌ Bybarter Error: 'data-api-key' attribute is missing from your tracking script installation tag.");
  }

  // 1. Automatically look at the URL bar to catch incoming affiliate marketers
  const urlParams = new URLSearchParams(window.location.search);
  const promoCode = urlParams.get("coop_ref") || urlParams.get("ref");

  if (promoCode) {
    localStorage.setItem("cooplead_referrer_code", promoCode);
    console.log(`🎯 Captured referral code: ${promoCode}`);
  }

  // 2. Expose the global helper function for manual tracking calls
  window.Cooplead = {
    trackEvent: function (eventName, customerUserId) {
      if (!customerUserId) {
        console.error("❌ Bybarter: customerUserId is strictly required for accurate conversion tracking.");
        return;
      }

      // Only attach the promo code from localStorage if we are initializing a 'sign_up' handshake.
      let referrerCode = undefined;
      if (eventName === "sign_up") {
        referrerCode = localStorage.getItem("cooplead_referrer_code");
        if (!referrerCode) {
          console.warn("⚠️ Bybarter: No referrer code found in local storage for this sign_up event.");
        }
      }

      console.log(`📤 Dispatching event [${eventName}] for Customer ID [${customerUserId}] to Bybarter core...`);

      // Points directly to your secure webhook receiver router
      fetch("http://127.0.0.1:5000/api/v1/webhook", { 
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${companyApiKey}` // 🚀 Automatically authenticates using the tag key
        },
        body: JSON.stringify({
          event_name: eventName,
          customer_user_id: String(customerUserId),
          referrer_code: referrerCode
        })
      })
      .then(res => res.json())
      .then(data => console.log("✅ Bybarter tracking response:", data))
      .catch(err => console.error("❌ Bybarter tracking failed:", err));
    }
  };

  // 🚀 3. AUTOMATED ELEMENT SELECTOR ENGINE
  function setupAutomatedSelectors() {
    if (!companyApiKey) {
      console.warn("⚠️ Bybarter: Skipping rule fetch because data-api-key is missing.");
      return;
    }

    console.log("🔍 Bybarter: Fetching active dashboard rules...");

    
    
    // Updated URL to match your Flask blueprint route, including authorization headers
    fetch("http://127.0.0.1:5000/api/company/tracking-rules/tracker", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${companyApiKey}` // 🚀 Authorizes the GET request safely
      }
    })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP status ${res.status}`);
        return res.json();
      })
      .then(rules => {
        if (!Array.isArray(rules)) return;
        
        // Filter out webhook rules; only look at frontend DOM snippet configurations
        const frontendRules = rules.filter(r => r.type === "frontend" && r.selector);
        console.log(`📋 Bybarter: Found ${frontendRules.length} active DOM rules to bind.`);

        frontendRules.forEach(rule => {
          const element = document.querySelector(rule.selector);
          
          if (element) {
            if (rule.eventName !== "sign_up") {
              console.warn(`💡 Bybarter Note: Automated selector "${rule.selector}" for custom event "${rule.eventName}" detected. Ensure your app handles user context mapping.`);
            }

            console.log(`🎯 Bybarter Target Locked! Auto-binding to element: "${rule.selector}" for event: "${rule.eventName}"`);
            
            // Prevent binding duplicate event listeners if script runs multiple times
            if (!element.dataset.coopleadBound) {
              element.dataset.coopleadBound = "true";
              element.addEventListener("click", () => {
                console.log(`💥 Auto-tracked element click detected via selector: ${rule.selector}`);
                
                // Read identifying data context directly from element properties or fallbacks
                const embeddedUserId = element.dataset.userId || window.currentBybarterUserId || "ANONYMOUS_FRONTEND_USER";
                
                window.Cooplead.trackEvent(rule.eventName, embeddedUserId);
              });
            }
          } else {
            console.warn(`⏳ Bybarter: Element selector "${rule.selector}" is configured in dashboard but not found on this page yet.`);
          }
        });
      })
      .catch(err => console.error("❌ Bybarter: Failed to fetch automated dashboard rules:", err));
  }

  // Run the selector scanner as soon as the DOM finishes loading
  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", setupAutomatedSelectors);
  } else {
    setupAutomatedSelectors();
  }

  // Fallback check for single-page applications where elements load dynamically later
  setTimeout(setupAutomatedSelectors, 2000);

  // Process any pending queues that fired via local recovery models before script finished loading
  const pendingSignup = localStorage.getItem("bybarter_pending_signup_id");
  if (pendingSignup) {
    console.log("🔄 Found a pending signup conversion in queue. Processing now...");
    window.Cooplead.trackEvent("sign_up", pendingSignup);
    localStorage.removeItem("bybarter_pending_signup_id");
  }
})();
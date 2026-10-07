/**
 * TUGON AI - Citizen Portal Frontend Logic
 * Real-time Geolocation, Camera EXIF Capture, and Multimodal Live Preview
 * Includes citizen authentication gate
 */

document.addEventListener("DOMContentLoaded", () => {
  // Check for citizen authentication — redirect if not logged in
  const citizenUser = localStorage.getItem("tugon_citizen_user");
  if (!citizenUser) {
    window.location.href = "/citizen/login";
    return;
  }

  // State
  let authenticatedUser = null;
  try {
    authenticatedUser = JSON.parse(citizenUser);
  } catch (e) {
    window.location.href = "/citizen/login";
    return;
  }

  let citizenLat = null;
  let citizenLon = null;
  let selectedFile = null;
  let debounceTimer = null;

  // DOM Elements
  const form = document.getElementById("incidentForm");
  const reportTitle = document.getElementById("reportTitle");
  const reportDesc = document.getElementById("reportDesc");
  const citizenName = document.getElementById("citizenName");
  const citizenContact = document.getElementById("citizenContact");
  
  const cameraInput = document.getElementById("cameraInput");
  const fileInput = document.getElementById("fileInput");
  const dropzone = document.getElementById("dropzone");
  const previewContainer = document.getElementById("previewContainer");
  const imagePreview = document.getElementById("imagePreview");
  const btnRemoveImage = document.getElementById("btnRemoveImage");
  
  const gpsDot = document.getElementById("gpsDot");
  const gpsStatusText = document.getElementById("gpsStatusText");
  const gpsCoords = document.getElementById("gpsCoords");
  const btnRefreshGps = document.getElementById("btnRefreshGps");
  
   // AI Preview elements
  const aiPredictedSector = document.getElementById("aiPredictedSector");
  const aiSectorDesc = document.getElementById("aiSectorDesc");
  const aiConfidenceText = document.getElementById("aiConfidenceText");
  const aiConfidenceBar = document.getElementById("aiConfidenceBar");
  const aiUrgencyBadge = document.getElementById("aiUrgencyBadge");
  const aiKeywordTags = document.getElementById("aiKeywordTags");
  const aiVisualCues = document.getElementById("aiVisualCues");

  // Form error notification
  const formErrorBox = document.createElement("div");
  formErrorBox.id = "formErrorBox";
  formErrorBox.style.cssText = "display:none;background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:8px;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.85rem;display:flex;align-items:center;gap:0.5rem;";
  formErrorBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i><span id="formErrorMsg"></span><button type="button" onclick="dismissFormError()" style="margin-left:auto;background:none;border:none;color:#dc2626;cursor:pointer;font-weight:700;">&times;</button>';
  if (form && form.parentNode) {
    form.parentNode.insertBefore(formErrorBox, form);
  }

  function showFormError(msg) {
    var msgEl = document.getElementById("formErrorMsg");
    if (msgEl) msgEl.textContent = msg;
    if (formErrorBox) formErrorBox.style.display = "flex";
    setTimeout(function() { if (formErrorBox) formErrorBox.style.display = "none"; }, 5000);
  }
  window.dismissFormError = function() {
    if (formErrorBox) formErrorBox.style.display = "none";
  };

  // EXIF Inspector elements
  const exifCamera = document.getElementById("exifCamera");
  const exifTimestamp = document.getElementById("exifTimestamp");
  const exifCoordinates = document.getElementById("exifCoordinates");

  // Modal elements
  const resultModal = document.getElementById("resultModal");
  const modalResultContent = document.getElementById("modalResultContent");
  const btnCloseModal = document.getElementById("btnCloseModal");

  // ==========================================
  // 1. Geolocation Acquisition
  // ==========================================
  function acquireGeolocation() {
    if (!navigator.geolocation) {
      gpsStatusText.textContent = "Geolocation not supported by browser";
      gpsCoords.textContent = "Please allow location manually";
      gpsDot.classList.remove("active", "pulse");
      return;
    }

    gpsStatusText.textContent = "Acquiring live device GPS...";
    gpsCoords.textContent = "Requesting satellite/cellular lock...";
    gpsDot.className = "gps-dot pulse";

    navigator.geolocation.getCurrentPosition(
      (position) => {
        citizenLat = position.coords.latitude;
        citizenLon = position.coords.longitude;
        const accuracy = position.coords.accuracy.toFixed(1);

        gpsDot.className = "gps-dot active";
        gpsStatusText.textContent = "Live Device GPS Acquired (High Precision)";
        gpsCoords.textContent = `Lat: ${citizenLat.toFixed(6)}°, Lon: ${citizenLon.toFixed(6)}° (±${accuracy}m)`;
      },
      (error) => {
        console.warn("Geolocation denied or unavailable:", error.message);
        // Default to Cebu City center fallback for testing convenience
        citizenLat = 10.3117;
        citizenLon = 123.8933;
        gpsDot.className = "gps-dot active";
        gpsStatusText.textContent = "Simulated Field GPS (Fuente Osmeña, Cebu City)";
        gpsCoords.textContent = `Lat: ${citizenLat.toFixed(4)}°, Lon: ${citizenLon.toFixed(4)}° (Cebu City Center fallback)`;
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }

  btnRefreshGps.addEventListener("click", acquireGeolocation);
  acquireGeolocation();

  // ==========================================
  // 2. Photo Handling & Preview
  // ==========================================
  function handleFileSelected(file) {
    if (!file || !file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPEG or PNG).");
      return;
    }

    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      previewContainer.style.display = "block";
      dropzone.style.display = "none";
    };
    reader.readAsDataURL(file);

     // Trigger instant preview analysis
    triggerLivePreview('image');
  }

  cameraInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
  });

  btnRemoveImage.addEventListener("click", () => {
    selectedFile = null;
    cameraInput.value = "";
    fileInput.value = "";
    previewContainer.style.display = "none";
    dropzone.style.display = "block";
    exifCamera.textContent = "None detected";
    exifTimestamp.textContent = "None";
    exifCoordinates.textContent = "None";
     aiVisualCues.textContent = "No image loaded.";
     triggerLivePreview('image');
  });

  // Drag & drop support
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  dropzone.addEventListener("click", (e) => {
    if (e.target.tagName !== "LABEL" && !e.target.closest("label")) {
      fileInput.click();
    }
  });

  // ==========================================
  // 3. Live AI Multimodal Preview
  // ==========================================
  function triggerLivePreview(triggerSource) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const title = reportTitle.value.trim();
      const desc = reportDesc.value.trim();

      // Trigger on image attachment, or when both text fields have meaningful content
      if (!selectedFile) {
        if (!title || !desc) return;
        const MIN_TITLE_LEN = 3;
        const MIN_DESC_LEN = 10;
        if (title.length < MIN_TITLE_LEN || desc.length < MIN_DESC_LEN) return;
      }

      const formData = new FormData();
      formData.append("title", title);
      formData.append("description", desc);
      if (selectedFile) {
        formData.append("photo", selectedFile);
      }

      // Show loading state in the AI preview card
      if (aiUrgencyBadge) {
        aiUrgencyBadge.textContent = "ANALYZING...";
        aiUrgencyBadge.className = "badge";
        aiUrgencyBadge.style.background = "rgba(56, 189, 248, 0.2)";
        aiUrgencyBadge.style.color = "#38bdf8";
      }

      try {
        const res = await fetch("/api/analyze-preview", {
          method: "POST",
          body: formData
        });
        if (!res.ok) {
          if (aiUrgencyBadge) { aiUrgencyBadge.textContent = "AWAITING INPUT"; aiUrgencyBadge.className = "badge"; aiUrgencyBadge.style.background = "rgba(255,255,255,0.15)"; aiUrgencyBadge.style.color = "#fff"; }
          return;
        }

        const data = await res.json();
        renderAIPreview(data);
      } catch (err) {
        console.error("Preview analysis error:", err);
        if (aiUrgencyBadge) { aiUrgencyBadge.textContent = "AWAITING INPUT"; aiUrgencyBadge.className = "badge"; aiUrgencyBadge.style.background = "rgba(255,255,255,0.15)"; aiUrgencyBadge.style.color = "#fff"; }
      }
    }, 350);
  }

   reportTitle.addEventListener("input", function() { triggerLivePreview('text'); });
   reportDesc.addEventListener("input", function() { triggerLivePreview('text'); });

  function renderAIPreview(data) {
    const cls = data.classification;
    const exif = data.exif_metadata;
    const sector = data.sector_meta || {};
    const office = data.office_meta || {};

    // Predicted Sector — show specific office name if available
    const displayName = office.short_name || cls.assigned_office || cls.predicted_sector;
    aiPredictedSector.textContent = displayName;
    const displayColor = office.color || sector.color;
    if (displayColor) {
      aiPredictedSector.style.background = `${displayColor}20`;
      aiPredictedSector.style.borderColor = `${displayColor}40`;
      aiPredictedSector.style.color = displayColor;
    }
    // Description: prefer office description, fall back to sector description
    aiSectorDesc.textContent = office.description || sector.description || "Incident assigned by AI multimodal intent analyzer.";

    // Confidence
    const confPercent = Math.round(cls.confidence * 100);
    aiConfidenceText.textContent = `${confPercent}%`;
    aiConfidenceBar.style.width = `${confPercent}%`;

    // Urgency
    aiUrgencyBadge.textContent = `${cls.urgency} PRIORITY`;
    aiUrgencyBadge.className = `badge badge-urgency-${cls.urgency}`;

    // Matched NLP Keywords
    if (cls.matched_keywords && cls.matched_keywords.length > 0) {
      aiKeywordTags.innerHTML = cls.matched_keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join("");
    } else {
      aiKeywordTags.innerHTML = `<span class="keyword-tag">general text input</span>`;
    }

    // Visual Cues
    if (cls.visual_cues && cls.visual_cues.length > 0) {
      aiVisualCues.innerHTML = cls.visual_cues.map(c => `<div><i class="fa-solid fa-eye" style="color: #38bdf8;"></i> ${c}</div>`).join("");
    } else if (selectedFile) {
      aiVisualCues.textContent = "Image loaded; color profile analyzed.";
    } else {
      aiVisualCues.textContent = "No image attached.";
    }

    // Requirements Checklist Preview — suggests specific documents (Valid ID, PSA, etc.)
    const aiReqList = document.getElementById("aiRequirementsList");
    if (aiReqList) {
      const aiReqs = cls.requirements || [];
      let reqs = aiReqs.length ? aiReqs : [];

      // Suggest standard documents based on predicted sector
      const sector = cls.predicted_sector || "";
      const standardDocs = ["Valid Government Photo ID (e.g. Passport, Driver's License, UBPIN)"];

      if (sector.includes("FIRST_RESPONDERS") || sector.includes("INFRASTRUCTURE") ||
          sector.includes("PUBLIC_HEALTH") || sector.includes("SOCIAL_WELFARE")) {
        standardDocs.push("Barangay Certificate of Residency", "Proof of Address (Utility Bill/Electricity Bill)");
      }
      if (sector.includes("AGRICULTURE") || sector.includes("INFRASTRUCTURE")) {
        standardDocs.push("PSA (Community Tax Certificate)");
      }
      if (sector.includes("PUBLIC_HEALTH")) {
        standardDocs.push("Medical Certificate (if health-related injury)");
      }

      if (reqs.length === 0) {
        reqs = standardDocs;
      } else {
        // Merge AI requirements with standard docs (avoid duplicates)
        const seen = new Set(reqs.map(r => r.toLowerCase()));
        for (const doc of standardDocs) {
          if (!seen.has(doc.toLowerCase())) {
            reqs.push(doc);
            seen.add(doc.toLowerCase());
          }
        }
      }

      aiReqList.innerHTML = reqs
        .map(r => `<li style="margin-bottom: 2px;">• ${r}</li>`)
        .join("");
    }

    // EXIF Metadata Inspector
    if (exif && exif.has_exif) {

      exifCamera.textContent = `${exif.camera_make || 'Unknown'} ${exif.camera_model || ''}`.trim() || 'Detected';
      exifTimestamp.textContent = exif.datetime_original || 'Embedded in EXIF';
      if (exif.lat !== null && exif.lon !== null) {
        exifCoordinates.textContent = `${exif.lat.toFixed(6)}° N, ${exif.lon.toFixed(6)}° E`;
        exifCoordinates.style.color = "#10b981";
      } else {
        exifCoordinates.textContent = "Location stripped / privacy mode";
        exifCoordinates.style.color = "#f59e0b";
      }
    } else if (selectedFile) {
      exifCamera.textContent = "Standard Web/Mobile Image";
      exifTimestamp.textContent = "Uploaded just now";
      exifCoordinates.textContent = "No EXIF GPS (Fallback will use device GPS)";
      exifCoordinates.style.color = "#f59e0b";
    }
  }

  // ==========================================
  // 4. Form Submission
  // ==========================================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = reportTitle.value.trim();
    const desc = reportDesc.value.trim();
    if (!title || !desc) {
      showFormError("Your report is missing a title and/or description. Please fill both fields before submitting.");
      if (!confirm("Your report is missing a title or description. Submit anyway?")) {
        return;
      }
    }

    const btnSubmit = document.getElementById("btnSubmit");
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing Evidence & Verifying GPS...`;

    const formData = new FormData();
    formData.append("title", title);
    formData.append("description", desc);
    // Pre-fill from authenticated citizen session
    const citizenFullName = authenticatedUser?.full_name || citizenName.value.trim() || "Anonymous Citizen";
    const citizenPhone = authenticatedUser?.phone_number || citizenContact.value.trim() || "N/A";
    formData.append("citizen_name", citizenFullName);
    formData.append("citizen_contact", citizenPhone);

    if (citizenLat !== null && citizenLon !== null) {
      formData.append("citizen_lat", citizenLat);
      formData.append("citizen_lon", citizenLon);
    }

    if (selectedFile) {
      formData.append("photo", selectedFile);
    }

    try {
      const res = await fetch("/api/reports", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        throw new Error(`Submission failed with status: ${res.status}`);
      }

      const result = await fetchSubmissionResult(res);
      renderResultModal(result);

      // Reset form
      form.reset();
      btnRemoveImage.click();
    } catch (err) {
      alert(`Submission Error: ${err.message}`);
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit Incident to TUGON AI`;
    }
  });

  async function fetchSubmissionResult(res) {
    return await res.json();
  }

  function renderResultModal(result) {
    const r = result.report;
    const notif = result.dispatched_notification;

    let verifBadgeClass = `badge-verif-${r.verification_status}`;
    let verifIcon = '<i class="fa-solid fa-shield-check"></i>';
    if (r.verification_status === "GPS_DISCREPANCY_FLAGGED") {
      verifIcon = '<i class="fa-solid fa-triangle-exclamation"></i>';
    } else if (r.verification_status === "EXIF_MISSING_FALLBACK_ACTIVE") {
      verifIcon = '<i class="fa-solid fa-circle-info"></i>';
    }

    const submittedAt = new Date().toLocaleString('en-PH', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });

    modalResultContent.innerHTML = `
      <div style="background: #dcfce8; border: 1px solid #86efac; border-radius: var(--radius-md); padding: 0.85rem; margin-bottom: 1.5rem; display: flex; align-items: flex-start; gap: 0.6rem;">
        <div style="color: #15803d; font-size: 1.4rem; flex-shrink: 0; margin-top: 0.1rem;">
          <i class="fa-solid fa-circle-check"></i>
        </div>
        <div style="flex: 1;">
          <div style="font-weight: 700; color: #14532d; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.4rem;">
            <i class="fa-solid fa-paper-plane"></i> Report Submitted Successfully
          </div>
          <div style="color: #166534; font-size: 0.85rem; line-height: 1.4;">
            Your report has been <strong>received and is now being triaged</strong> by the AI forensic verification engine.
          </div>
          ${notif ? `<div style="color: #166534; font-size: 0.82rem; margin-top: 0.3rem;"><strong>Sector Dispatch:</strong> Notification sent to ${notif.recipient_sector} (${notif.recipient_email}).</div>` : ''}
          <div style="color: #166534; font-size: 0.82rem; margin-top: 0.3rem;">
            <i class="fa-solid fa-clock"></i> Submitted: ${submittedAt}
          </div>
        </div>
      </div>

      <div style="text-align: center; margin-bottom: 1.5rem;">
        <div style="font-size: 0.85rem; color: var(--slate-500); text-transform: uppercase; font-weight: 700;">Incident Tracking ID</div>
        <div style="font-size: 1.75rem; font-weight: 800; color: #2563eb; font-family: monospace;">${r.ticket_number}</div>
        <div style="margin-top: 0.5rem;">
          <span class="badge ${verifBadgeClass}">${verifIcon} ${r.verification_status.replace(/_/g, ' ')}</span>
          <span class="badge badge-urgency-${r.urgency}" style="margin-left: 0.5rem;">${r.urgency} PRIORITY</span>
        </div>
      </div>

      <div class="forensic-audit-panel">
        <h4 style="font-size: 0.9rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--slate-800);">
          <i class="fa-solid fa-brain" style="color: #2563eb;"></i> AI Multimodal Classification & Routing
        </h4>
        <div class="forensic-metric-row">
          <span>Assigned Municipal Sector:</span>
          <strong>${r.category}</strong>
        </div>
        <div class="forensic-metric-row">
          <span>AI Fusion Confidence:</span>
          <strong style="color: #10b981;">${Math.round(r.confidence * 100)}%</strong>
        </div>
        <div class="forensic-metric-row">
          <span>Resolved Location:</span>
          <span>${r.address}</span>
        </div>
        ${r.gps_distance_m !== null ? `
        <div class="forensic-metric-row">
          <span>EXIF vs Device Distance Delta:</span>
          <strong style="color: ${r.gps_distance_m <= 200 ? '#10b981' : '#ef4444'};">${r.gps_distance_m} meters</strong>
        </div>
        ` : ''}
        <div style="font-size: 0.8rem; color: var(--slate-600); margin-top: 0.5rem; line-height: 1.4;">
          <strong>Forensic Notes:</strong> ${r.verification_notes}
        </div>
      </div>

      <!-- Requirements Advisory Checklist Panel (Objective 4 / Question 4.4) -->
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 0.85rem; margin-top: 1rem; font-size: 0.82rem;">
        <div style="font-weight: 700; color: #0284c7; margin-bottom: 0.35rem;">
          <i class="fa-solid fa-list-check"></i> Pre-requisite Requirements to Prepare for ${r.assigned_office || 'Assigned Office'}:
        </div>
        <ul style="margin: 0; padding-left: 1.2rem; color: #334155; line-height: 1.4;">
          ${(function(){
            let reqs = [];
            try {
              let parsed = JSON.parse(r.multimodal_breakdown || '{}');
              reqs = parsed.requirements || [];
            } catch(e){}

            const sector = r.category || '';
            const standardDocs = ["Valid Government Photo ID (e.g. Passport, Driver's License, UBPIN)", "Incident Photo Evidence"];

            if (sector.includes("FIRST_RESPONDERS") || sector.includes("INFRASTRUCTURE") ||
                sector.includes("PUBLIC_HEALTH") || sector.includes("SOCIAL_WELFARE")) {
              standardDocs.push("Proof of Address (Utility Bill)");
            }
            if (sector.includes("AGRICULTURE") || sector.includes("INFRASTRUCTURE")) {
              standardDocs.push("PSA (Community Tax Certificate)");
            }
            if (sector.includes("PUBLIC_HEALTH")) {
              standardDocs.push("Medical Certificate (if injury)");
            }

            if (!reqs.length) {
              reqs = standardDocs;
            } else {
              const seen = new Set(reqs.map(r => r.toLowerCase()));
              for (const doc of standardDocs) {
                if (!seen.has(doc.toLowerCase())) reqs.push(doc);
              }
            }
            return reqs.map(item => `<li>${item}</li>`).join('');
          })()}
        </ul>
      </div>

      <!-- ReAct Cognitive Trace Log (Yao et al., 2022) -->
      <div style="background: #0f172a; color: #38bdf8; border-radius: var(--radius-md); padding: 0.85rem; margin-top: 1rem; font-family: monospace; font-size: 0.73rem;">
        <div style="font-weight: 700; color: #f8fafc; margin-bottom: 0.35rem; display: flex; align-items: center; justify-content: space-between;">
          <span><i class="fa-solid fa-diagram-project"></i> ReAct Agent Cognitive Loop Trace</span>
          <span style="font-size: 0.65rem; color: #94a3b8;">AOCM 80% Automated</span>
        </div>
        ${(function(){
          let trace = [];
          try {
            let parsed = JSON.parse(r.multimodal_breakdown || '{}');
            trace = parsed.react_trace || [];
          } catch(e){}
          if (!trace.length) return '<div style="color: #94a3b8;">ReAct execution trace logged.</div>';
          return trace.map(t => `<div style="margin-bottom: 2px;"><span style="color:#f59e0b;">[${t.step}]</span> ${t.details}</div>`).join('');
        })()}
      </div>

      <div style="display: flex; gap: 0.75rem; margin-top: 1.5rem;">
        <button class="btn btn-outline btn-block" onclick="document.getElementById('resultModal').classList.remove('active')">
          Submit Another Report
        </button>
        <a href="/dashboard" class="btn btn-primary btn-block">
          <i class="fa-solid fa-gauge-high"></i> View in Command Dashboard
        </a>
      </div>
    `;

    resultModal.classList.add("active");
  }

  btnCloseModal.addEventListener("click", () => {
    resultModal.classList.remove("active");
  });

  resultModal.addEventListener("click", (e) => {
    if (e.target === resultModal) resultModal.classList.remove("active");
  });

  // ==========================================
  // 5. Citizen Logout
  // ==========================================
  const btnCitizenLogout = document.getElementById("btnCitizenLogout");
  if (btnCitizenLogout) {
    btnCitizenLogout.addEventListener("click", () => {
      if (confirm("Sign out from your citizen account?")) {
        localStorage.removeItem("tugon_citizen_user");
        window.location.href = "/citizen/login";
      }
    });
  }

  // Auto-fill citizen display name in the form label
  if (authenticatedUser?.full_name) {
    const nameHint = document.querySelector('[for="citizenName"]') ||
                     document.querySelector('.form-label');
    if (nameHint) {
      nameHint.innerHTML = 'Pangalan <small style="color: var(--slate-400); font-weight:400;">(' +
        authenticatedUser.full_name + ')</small>';
    }
  }
});


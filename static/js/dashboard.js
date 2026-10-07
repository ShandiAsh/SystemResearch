/**
 * TUGON AI - Sector Command & Forensic Audit Dashboard Logic
 * Leaflet Geospatial Map, Real-time Tally, Forensic Audit Inspector, and Sector Dispatch
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let allReports = [];
  let currentSectorFilter = "ALL";
  let currentVerifFilter = "ALL";
  let map = null;
  let markersLayer = null;

   // DOM Elements
  const sectorTallyList = document.getElementById("sectorTallyList");
  const reportsTableBody = document.getElementById("reportsTableBody");
  const sectorTabs = document.getElementById("sectorTabs");
  const filterVerifStatus = document.getElementById("filterVerifStatus");
  const reportSearchInput = document.getElementById("reportSearchInput");
  const btnResetMapView = document.getElementById("btnResetMapView");

  // Modals
  const forensicModal = document.getElementById("forensicModal");
  const forensicModalBody = document.getElementById("forensicModalBody");
  const btnCloseForensicModal = document.getElementById("btnCloseForensicModal");

  const notificationModal = document.getElementById("notificationModal");
  const notificationModalBody = document.getElementById("notificationModalBody");
  const btnOpenNotificationLogs = document.getElementById("btnOpenNotificationLogs");
  const btnCloseNotificationModal = document.getElementById("btnCloseNotificationModal");

  // ==========================================
  // 1. Initialize Geospatial Leaflet Map
  // ==========================================
  function initMap() {
    // Cebu City Center coordinates (Fuente Osmeña Circle)
    const defaultCenter = [10.3117, 123.8933];
    map = L.map("dashboardMap").setView(defaultCenter, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | TUGON AI Cebu City',
      maxZoom: 18
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);

    btnResetMapView.addEventListener("click", () => {
      map.setView(defaultCenter, 13);
    });
  }

  initMap();

  // ==========================================
  // 2. Fetch Analytics & Reports
  // ==========================================
  async function loadDashboardData() {
    try {
      const [analyticsRes, reportsRes] = await Promise.all([
        fetch("/api/analytics"),
        fetch("/api/reports")
      ]);

      const analytics = await analyticsRes.json();
      allReports = await reportsRes.json();

      renderAnalytics(analytics);
      renderMapPins(allReports);
      filterAndRenderReports();
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    }
  }

   function renderAnalytics(analytics) {
    const secMeta = analytics.sectors_meta || {};
    const officeMeta = analytics.offices_meta || {};
    const counts = analytics.sector_breakdown || {};
    const officeCounts = analytics.office_breakdown || {};
    const total = Math.max(analytics.total_reports || 1, 1);

    let html = '';
    for (const [key, count] of Object.entries(counts)) {
      const meta = secMeta[key] || { name: key, color: "#3b82f6" };
      const pct = Math.round((count / total) * 100);
      const catOffices = (meta.offices || []);

      let officeSubRows = '';
      catOffices.forEach(offKey => {
        const oMeta = officeMeta[offKey] || { short_name: offKey, color: "#94a3b8" };
        const oCount = officeCounts[offKey] || 0;
        officeSubRows += `
          <div style="display: flex; justify-content: space-between; margin: 2px 0 2px 12px; font-size: 0.73rem; color: var(--slate-500);">
            <span>↳ ${oMeta.short_name || offKey}</span>
            <span style="font-weight: 600;">${oCount}</span>
          </div>`;
      });

      html += `
        <div style="margin-bottom: 0.9rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
            <span class="sector-tally-name" style="font-weight: 700; color: ${meta.color}; font-size: 0.82rem; cursor: pointer;" data-sector="${key}" title="Click to filter reports by ${meta.name || key}">${meta.name || key} <i class="fa-solid fa-filter-circle-xmark" style="font-size: 0.7rem; opacity: 0.5;"></i></span>
            <span style="font-weight: 600; color: var(--slate-700);">${count} (${pct}%)</span>
          </div>
          <div style="height: 6px; background: var(--slate-100); border-radius: 9999px; overflow: hidden; margin-bottom: 4px;">
            <div style="height: 100%; width: ${pct}%; background: ${meta.color}; border-radius: 9999px;"></div>
          </div>
          ${officeSubRows}
        </div>
      `;
    }
    sectorTallyList.innerHTML = html || '<div style="color: var(--slate-400);">No sector data recorded.</div>';

    // Add click handlers for sector tally names
    sectorTallyList.querySelectorAll('.sector-tally-name').forEach(el => {
      el.addEventListener('click', function() {
        const sectorKey = this.getAttribute('data-sector');
        currentSectorFilter = sectorKey;
        filterAndRenderReports();
      });
    });
  }

  // ==========================================
  // 3. Map Marker Rendering
  // ==========================================
  function renderMapPins(reports) {
    markersLayer.clearLayers();

    reports.forEach(r => {
      const lat = r.exif_lat || r.citizen_lat;
      const lon = r.exif_lon || r.citizen_lon;

      if (!lat || !lon) return;

      // Color code pin by urgency
      let pinColor = "#3b82f6";
      if (r.urgency === "CRITICAL") pinColor = "#ef4444";
      else if (r.urgency === "HIGH") pinColor = "#f97316";
      else if (r.urgency === "LOW") pinColor = "#10b981";

      const circleMarker = L.circleMarker([lat, lon], {
        radius: r.urgency === "CRITICAL" ? 10 : 8,
        fillColor: pinColor,
        color: "#ffffff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85
      });

      const popupContent = `
        <div style="font-family: sans-serif; font-size: 13px; max-width: 220px;">
          <div style="font-weight: 800; color: #2563eb; margin-bottom: 2px;">${r.ticket_number}</div>
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">${r.title}</div>
          <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">${r.address}</div>
          <div style="display: flex; gap: 4px; margin-bottom: 8px;">
            <span class="badge badge-urgency-${r.urgency}" style="font-size: 10px;">${r.urgency}</span>
            <span class="badge" style="background: #0f172a; color: white; font-size: 10px;">${r.category}</span>
          </div>
          <button class="btn btn-primary btn-sm btn-block" onclick="window.inspectReport(${r.id})">
            Audit Forensics
          </button>
        </div>
      `;

      circleMarker.bindPopup(popupContent);
      markersLayer.addLayer(circleMarker);
    });
  }

  // ==========================================
  // 4. Filter & Render Table
  // ==========================================
  function filterAndRenderReports() {
    let filtered = allReports;

    if (currentSectorFilter !== "ALL") {
      filtered = filtered.filter(r => r.category === currentSectorFilter);
    }

    if (currentVerifFilter !== "ALL") {
      filtered = filtered.filter(r => r.verification_status === currentVerifFilter);
    }

    // Search filter
    const searchInput = document.getElementById("reportSearchInput");
    if (searchInput && searchInput.value.trim()) {
      const searchTerm = searchInput.value.trim().toLowerCase();
      filtered = filtered.filter(r =>
        (r.ticket_number || "").toLowerCase().includes(searchTerm) ||
        (r.title || "").toLowerCase().includes(searchTerm) ||
        (r.category || "").toLowerCase().includes(searchTerm) ||
        (r.description || "").toLowerCase().includes(searchTerm)
      );
    }

    if (filtered.length === 0) {
      reportsTableBody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; color: var(--slate-400); padding: 2.5rem;">
            <i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
            No reports match the selected filters.
          </td>
        </tr>
      `;
      return;
    }

    let rowsHtml = '';
    filtered.forEach(r => {
      const photoThumb = r.photo_url 
        ? `<img src="${r.photo_url}" style="width: 52px; height: 52px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--slate-200); cursor: pointer;" onclick="window.inspectReport(${r.id})">`
        : `<div style="width: 52px; height: 52px; background: var(--slate-100); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; color: var(--slate-400);"><i class="fa-solid fa-image"></i></div>`;

      // Sector Category Color Map (5 new categories)
      const SECTOR_COLORS = {
        FIRST_RESPONDERS: "#ef4444",
        SOCIAL_WELFARE: "#f59e0b",
        PUBLIC_HEALTH: "#06b6d4",
        INFRASTRUCTURE_UTILITIES: "#10b981",
        AGRICULTURE_ANIMAL: "#8b5cf6"
      };
      const secColor = SECTOR_COLORS[r.category] || "#3b82f6";

      // Office short label (if available from analytics offices_meta)
      const officeLabel = r.assigned_office || r.category || "—";

      const verifBadge = `badge-verif-${r.verification_status}`;
      const shortVerif = r.verification_status.replace(/_/g, ' ');

      const formattedDate = r.created_at ? new Date(r.created_at).toLocaleString() : 'Recent';

      rowsHtml += `
        <tr>
          <td class="cell-nowrap" style="font-family: monospace; font-weight: 700; color: #2563eb;">${r.ticket_number}</td>
          <td class="cell-nowrap">${photoThumb}</td>
          <td class="cell-details">
            <div class="text-title-2lines" style="font-weight: 700; color: var(--slate-900);">${r.title}</div>
            <div class="text-addr-2lines" style="font-size: 0.775rem; color: var(--slate-500);">${r.address}</div>
          </td>
          <td class="cell-nowrap">
            <span class="badge-sector" style="background: ${secColor};">${r.category || '—'}</span>
            <div style="font-size: 0.7rem; color: var(--slate-500); margin-top: 3px;">${officeLabel !== r.category ? officeLabel : ''}</div>
          </td>
          <td class="cell-nowrap">
            <span style="font-weight: 700; color: #059669;">${Math.round(r.confidence * 100)}%</span>
          </td>
          <td class="cell-nowrap">
            <span class="badge badge-urgency-${r.urgency}">${r.urgency}</span>
          </td>
          <td class="cell-nowrap">
            <span class="badge ${verifBadge}">${shortVerif}</span>
            ${r.gps_distance_m !== null ? `<div style="font-size: 0.7rem; color: var(--slate-500); margin-top: 2px;">Delta: ${r.gps_distance_m}m</div>` : ''}
          </td>
          <td class="cell-nowrap">
            <span style="font-weight: 600; font-size: 0.8rem; color: var(--slate-700);">${r.status}</span>
          </td>
          <td style="text-align: right;">
            <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
              <button class="btn btn-outline btn-sm" onclick="window.inspectReport(${r.id})" title="Inspect EXIF & Forensics">
                <i class="fa-solid fa-microscope"></i> Audit
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.dispatchNotification(${r.id})" title="Trigger Dispatch Email">
                <i class="fa-solid fa-paper-plane"></i> Dispatch
              </button>
            </div>
          </td>
        </tr>
      `;
    });

    reportsTableBody.innerHTML = rowsHtml;
  }

  // Filter Event Listeners
  sectorTabs.addEventListener("click", (e) => {
    if (e.target.classList.contains("tab-pill")) {
      document.querySelectorAll("#sectorTabs .tab-pill").forEach(p => p.classList.remove("active"));
      e.target.classList.add("active");
      currentSectorFilter = e.target.getAttribute("data-sector");
      filterAndRenderReports();
    }
  });

  filterVerifStatus.addEventListener("change", (e) => {
    currentVerifFilter = e.target.value;
    filterAndRenderReports();
  });

  // Search bar
  if (reportSearchInput) {
    reportSearchInput.addEventListener("input", () => {
      filterAndRenderReports();
    });
  }

  // ==========================================
  // 5. Forensic Inspection Modal
  // ==========================================
  window.inspectReport = async function(reportId) {
    try {
      const res = await fetch(`/api/reports/${reportId}`);
      if (!res.ok) throw new Error("Could not load report details.");
      const r = await res.json();

      let parsedExif = {};
      try {
        parsedExif = JSON.parse(r.exif_data || "{}");
      } catch (e) {}

      let parsedBreakdown = {};
      try {
        parsedBreakdown = JSON.parse(r.multimodal_breakdown || "{}");
      } catch (e) {}

      const mapLat = r.exif_lat || r.citizen_lat;
      const mapLon = r.exif_lon || r.citizen_lon;
      const googleMapsUrl = mapLat && mapLon ? `https://www.google.com/maps/search/?api=1&query=${mapLat},${mapLon}` : "#";

      forensicModalBody.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
          
          <!-- Column 1: Media Evidence & Forensic Metadata -->
          <div>
            <div style="position: relative; border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--slate-200); margin-bottom: 1rem;">
              ${r.photo_url 
                ? `<img src="${r.photo_url}" style="width: 100%; max-height: 280px; object-fit: cover; display: block;">` 
                : `<div style="padding: 3rem; text-align: center; color: var(--slate-400); background: var(--slate-100);">No photo evidence attached</div>`
              }
              <div style="position: absolute; bottom: 8px; right: 8px;">
                <span class="badge badge-verif-${r.verification_status}">
                  ${r.verification_status.replace(/_/g, ' ')}
                </span>
              </div>
            </div>

            <!-- EXIF Camera Metadata Table -->
            <div class="card" style="margin-bottom: 1rem;">
              <div class="card-header" style="padding: 0.75rem 1rem;">
                <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--slate-800);">
                  <i class="fa-solid fa-fingerprint" style="color: #10b981;"></i> Forensic EXIF Metadata
                </h4>
              </div>
              <div class="card-body" style="padding: 0.75rem 1rem; font-size: 0.8rem;">
                <div class="forensic-metric-row">
                  <span style="color: var(--slate-500);">Camera Hardware:</span>
                  <strong>${parsedExif.camera_make || 'Unknown'} ${parsedExif.camera_model || ''}</strong>
                </div>
                <div class="forensic-metric-row">
                  <span style="color: var(--slate-500);">Capture Timestamp:</span>
                  <strong>${parsedExif.datetime_original || 'Not specified'}</strong>
                </div>
                <div class="forensic-metric-row">
                  <span style="color: var(--slate-500);">Photo EXIF GPS:</span>
                  <span style="font-family: monospace; color: #2563eb;">
                    ${r.exif_lat ? `${r.exif_lat.toFixed(6)}°, ${r.exif_lon.toFixed(6)}°` : 'None (Privacy Mode)'}
                  </span>
                </div>
                <div class="forensic-metric-row">
                  <span style="color: var(--slate-500);">Device Submission GPS:</span>
                  <span style="font-family: monospace; color: #059669;">
                    ${r.citizen_lat ? `${r.citizen_lat.toFixed(6)}°, ${r.citizen_lon.toFixed(6)}°` : 'Not provided'}
                  </span>
                </div>
                <div class="forensic-metric-row">
                  <span style="color: var(--slate-500);">Haversine Delta Distance:</span>
                  <strong style="color: ${r.gps_distance_m !== null && r.gps_distance_m > 200 ? '#ef4444' : '#059669'};">
                    ${r.gps_distance_m !== null ? `${r.gps_distance_m} meters` : 'N/A'}
                  </strong>
                </div>
              </div>
            </div>

            <div style="font-size: 0.8rem; color: var(--slate-600); background: var(--slate-50); border: 1px solid var(--slate-200); padding: 0.75rem; border-radius: var(--radius-sm);">
              <strong>Forensic Audit Assessment:</strong><br>
              ${r.verification_notes}
            </div>
          </div>

          <!-- Column 2: AI Classification, Incident Narrative & Action Panel -->
          <div>
            <div style="margin-bottom: 1rem;">
              <span class="badge badge-urgency-${r.urgency}">${r.urgency} URGENCY</span>
              <span class="badge" style="background: var(--slate-900); color: white; margin-left: 0.4rem;">${r.status}</span>
              <div style="font-size: 1.15rem; font-weight: 800; color: var(--slate-900); margin-top: 0.4rem;">${r.title}</div>
              <div style="font-size: 0.85rem; color: var(--slate-500);"><i class="fa-solid fa-location-dot"></i> ${r.address}</div>
            </div>

            <!-- Citizen Description -->
            <div class="form-group">
              <label class="form-label">Citizen Complaint Narrative</label>
              <div style="background: var(--slate-50); border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 0.85rem; font-size: 0.85rem; line-height: 1.5; color: var(--slate-800);">
                "${r.description}"
              </div>
            </div>

            <!-- AI Classification Rationale -->
            <div class="card" style="margin-bottom: 1rem;">
              <div class="card-header" style="padding: 0.75rem 1rem;">
                <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--slate-800);">
                  <i class="fa-solid fa-brain" style="color: #2563eb;"></i> Multimodal AI Decision Rationale
                </h4>
              </div>
              <div class="card-body" style="padding: 0.75rem 1rem; font-size: 0.8rem;">
                <div class="forensic-metric-row">
                  <span>Sector Category:</span>
                  <strong>${r.category || '—'}</strong>
                </div>
                <div class="forensic-metric-row">
                  <span>Assigned Office:</span>
                  <strong style="color: #2563eb;">${r.assigned_office || '—'}</strong>
                </div>
                <div class="forensic-metric-row">
                  <span>Confidence Level:</span>
                  <strong style="color: #059669;">${Math.round(r.confidence * 100)}%</strong>
                </div>
                <div style="margin-top: 0.5rem;">
                  <span style="color: var(--slate-500); font-size: 0.75rem;">Vernacular Text Keywords:</span>
                  <div class="keyword-tags" style="margin-top: 0.25rem;">
                    ${(parsedBreakdown.keywords || []).map(k => `<span class="keyword-tag" style="background: #e2e8f0; color: #1e293b;">${k}</span>`).join('') || '<span class="keyword-tag">none</span>'}
                  </div>
                </div>
              </div>
            </div>

            <!-- Admin Status / Sector Update Controls -->
            <form id="updateStatusForm" onsubmit="window.submitStatusUpdate(event, ${r.id})">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                <div>
                  <label class="form-label" style="font-size: 0.75rem;">Lifecycle Status</label>
                  <select id="modalSelectStatus" class="form-control" style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
                    <option value="PENDING_REVIEW" ${r.status === 'PENDING_REVIEW' ? 'selected' : ''}>PENDING REVIEW</option>
                    <option value="VERIFIED" ${r.status === 'VERIFIED' ? 'selected' : ''}>VERIFIED</option>
                    <option value="DISPATCHED" ${r.status === 'DISPATCHED' ? 'selected' : ''}>DISPATCHED</option>
                    <option value="IN_PROGRESS" ${r.status === 'IN_PROGRESS' ? 'selected' : ''}>IN PROGRESS</option>
                    <option value="RESOLVED" ${r.status === 'RESOLVED' ? 'selected' : ''}>RESOLVED</option>
                    <option value="FLAGGED" ${r.status === 'FLAGGED' ? 'selected' : ''}>FLAGGED (FRAUD)</option>
                  </select>
                </div>
                <div>
                  <label class="form-label" style="font-size: 0.75rem;">Assigned Sector / Office</label>
                  <select id="modalSelectSector" class="form-control" style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
                    <optgroup label="── Sector Categories ──">
                      <option value="FIRST_RESPONDERS" ${r.category === 'FIRST_RESPONDERS' ? 'selected' : ''}>🚑 First Responders &amp; Emergency Rescue</option>
                      <option value="SOCIAL_WELFARE" ${r.category === 'SOCIAL_WELFARE' ? 'selected' : ''}>🤝 Relief, Food &amp; Social Welfare</option>
                      <option value="PUBLIC_HEALTH" ${r.category === 'PUBLIC_HEALTH' ? 'selected' : ''}>🏥 Medical Care &amp; Public Health</option>
                      <option value="INFRASTRUCTURE_UTILITIES" ${r.category === 'INFRASTRUCTURE_UTILITIES' ? 'selected' : ''}>🏗️ Infrastructure &amp; Utilities</option>
                      <option value="AGRICULTURE_ANIMAL" ${r.category === 'AGRICULTURE_ANIMAL' ? 'selected' : ''}>🌾 Farming, Animal &amp; Rural Aid</option>
                    </optgroup>
                    <optgroup label="── Specific Partner Offices ──">
                      <option value="CCDRRMO" ${r.assigned_office === 'CCDRRMO' ? 'selected' : ''}>CCDRRMO – Disaster Risk Reduction</option>
                      <option value="BFP" ${r.assigned_office === 'BFP' ? 'selected' : ''}>BFP – Bureau of Fire Protection</option>
                      <option value="CCTO" ${r.assigned_office === 'CCTO' ? 'selected' : ''}>CCTO – Transportation Office</option>
                      <option value="DSWD" ${r.assigned_office === 'DSWD' ? 'selected' : ''}>DSWD – Social Welfare &amp; Services</option>
                      <option value="NUTRITION" ${r.assigned_office === 'NUTRITION' ? 'selected' : ''}>Nutrition Office</option>
                      <option value="CHD" ${r.assigned_office === 'CHD' ? 'selected' : ''}>CHD – City Health Department</option>
                      <option value="CCMC" ${r.assigned_office === 'CCMC' ? 'selected' : ''}>CCMC – Cebu City Medical Center</option>
                      <option value="DEPW" ${r.assigned_office === 'DEPW' ? 'selected' : ''}>DEPW – Engineering &amp; Public Works</option>
                      <option value="DPS" ${r.assigned_office === 'DPS' ? 'selected' : ''}>DPS – Department of Public Services</option>
                      <option value="CAD" ${r.assigned_office === 'CAD' ? 'selected' : ''}>CAD – City Agriculture Department</option>
                      <option value="DVMF" ${r.assigned_office === 'DVMF' ? 'selected' : ''}>DVMF – Veterinary Medicine &amp; Fisheries</option>
                    </optgroup>
                  </select>
                </div>
              </div>

              <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                <button type="submit" class="btn btn-primary btn-sm btn-block">
                  <i class="fa-solid fa-floppy-disk"></i> Update Status
                </button>
                <a href="${googleMapsUrl}" target="_blank" class="btn btn-outline btn-sm">
                  <i class="fa-solid fa-map-pin"></i> Open Maps
                </a>
              </div>
            </form>

          </div>
        </div>
      `;

      forensicModal.classList.add("active");
    } catch (err) {
      alert(`Failed to load incident details: ${err.message}`);
    }
  };

  window.submitStatusUpdate = async function(event, reportId) {
    event.preventDefault();
    const newStatus = document.getElementById("modalSelectStatus").value;
    const assignedSector = document.getElementById("modalSelectSector").value;

    const formData = new FormData();
    formData.append("new_status", newStatus);
    formData.append("assigned_sector", assignedSector);

    try {
      const res = await fetch(`/api/reports/${reportId}/status`, {
        method: "PATCH",
        body: formData
      });
      if (!res.ok) throw new Error("Update failed.");

      forensicModal.classList.remove("active");
      await loadDashboardData();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  };

  btnCloseForensicModal.addEventListener("click", () => {
    forensicModal.classList.remove("active");
  });

  forensicModal.addEventListener("click", (e) => {
    if (e.target === forensicModal) forensicModal.classList.remove("active");
  });

  // ==========================================
  // 6. Manual Notification Dispatch Trigger
  // ==========================================
  window.dispatchNotification = async function(reportId) {
    if (!confirm(`Dispatch automated notification alert to sector for Ticket #${reportId}?`)) return;

    try {
      const res = await fetch(`/api/reports/${reportId}/dispatch`, {
        method: "POST"
      });
      const data = await res.json();
      alert(`Success: ${data.message}`);
      await loadDashboardData();
    } catch (err) {
      alert(`Dispatch error: ${err.message}`);
    }
  };

  // ==========================================
  // 7. Notification Logs Modal
  // ==========================================
  btnOpenNotificationLogs.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/notifications");
      const logs = await res.json();

      if (logs.length === 0) {
        notificationModalBody.innerHTML = `<div style="text-align: center; color: var(--slate-400); padding: 3rem;">No notification alerts dispatched yet.</div>`;
      } else {
        let html = '<div style="display: flex; flex-direction: column; gap: 1rem;">';
        logs.forEach(l => {
          html += `
            <div class="card" style="padding: 1rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="color: #2563eb; font-size: 0.95rem;">${l.subject}</strong>
                <span class="badge" style="background: #10b981; color: white;">${l.status}</span>
              </div>
              <div style="font-size: 0.8rem; color: var(--slate-500); margin-bottom: 0.75rem;">
                Recipient: <strong>${l.recipient_email}</strong> (${l.recipient_sector}) | Dispatched: ${new Date(l.sent_at).toLocaleString()}
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 1rem; max-height: 250px; overflow-y: auto;">
                ${l.body_html}
              </div>
            </div>
          `;
        });
        html += '</div>';
        notificationModalBody.innerHTML = html;
      }

      notificationModal.classList.add("active");
    } catch (err) {
      alert(`Failed to load notification logs: ${err.message}`);
    }
  });

  btnCloseNotificationModal.addEventListener("click", () => {
    notificationModal.classList.remove("active");
  });

  notificationModal.addEventListener("click", (e) => {
    if (e.target === notificationModal) notificationModal.classList.remove("active");
  });

   // Initial Data Load
   loadDashboardData();
   checkSuperadminAccess();

   // Auto-refresh every 30 seconds for live incident feed
   setInterval(loadDashboardData, 30000);
   setInterval(checkSuperadminAccess, 30000);
  });

  // Check if current admin user is SUPERADMIN and show analysis section
  function checkSuperadminAccess() {
    var adminUser = localStorage.getItem("tugon_admin_user");
    if (!adminUser) {
      window.location.href = "/login";
      return;
    }

    var user;
    try {
      user = JSON.parse(adminUser);
    } catch {
      window.location.href = "/login";
      return;
    }

    var section = document.getElementById("superadminAnalysisSection");
    if (!section) return;

    if (user.role === "SUPERADMIN") {
      section.style.display = "block";
      loadSuperadminAnalysis();
    } else {
      section.style.display = "none";
    }
  }

  // Fetch and render superadmin-only analysis
  function loadSuperadminAnalysis() {
    var content = document.getElementById("superadminAnalysisContent");
    if (!content) return;

    content.innerHTML = '<div style="text-align: center; padding: 1rem; color: var(--slate-400);"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';

    fetch("/api/analytics/superadmin?role=SUPERADMIN")
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (data.detail) {
          content.innerHTML = '<div style="color:#ef4444;"><i class="fa-solid fa-circle-exclamation"></i> ' + data.detail + '</div>';
          return;
        }

        var html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">';
        html += '<div style="background: #f8fafc; border-radius: 8px; padding: 1rem; text-align: center;"><div style="font-size: 1.5rem; font-weight: 800; color: #7c3aed;">' + data.total_reports + '</div><div style="font-size: 0.75rem; color: #64748b;">Total Incidents</div></div>';
        html += '<div style="background: #f8fafc; border-radius: 8px; padding: 1rem; text-align: center;"><div style="font-size: 1.5rem; font-weight: 800; color: #10b981;">' + data.verification_breakdown.VERIFIED_GENUINE + '</div><div style="font-size: 0.75rem; color: #64748b;">Verified Genuine</div></div>';
        html += '<div style="background: #f8fafc; border-radius: 8px; padding: 1rem; text-align: center;"><div style="font-size: 1.5rem; font-weight: 800; color: #ef4444;">' + data.verification_breakdown.GPS_DISCREPANCY_FLAGGED + '</div><div style="font-size: 0.75rem; color: #64748b;">GPS Flagged</div></div>';
        html += '<div style="background: #f8fafc; border-radius: 8px; padding: 1rem; text-align: center;"><div style="font-size: 1.5rem; font-weight: 800; color: #f59e0b;">' + (data.false_report_rate_pct || 0) + '%</div><div style="font-size: 0.75rem; color: #64748b;">False Report Rate</div></div>';
        html += '</div>';

        // AI Confidence Distribution
        html += '<h4 style="font-size: 0.9rem; font-weight: 700; color: var(--slate-700); margin: 1rem 0 0.5rem;">AI Confidence Distribution</h4>';
        html += '<div style="display: flex; gap: 0.25rem; margin-bottom: 1rem;">';
        Object.entries(data.confidence_distribution).forEach(function(entry) {
          html += '<div style="flex: 1; text-align: center; background: #f8fafc; border-radius: 6px; padding: 0.5rem; border: 1px solid #e2e8f0;"><div style="font-size: 1rem; font-weight: 700; color: #0284c7;">' + entry[1] + '</div><div style="font-size: 0.65rem; color: #64748b;">' + entry[0] + '</div></div>';
        });
        html += '</div>';

        // Per-Sector Analysis
        html += '<h4 style="font-size: 0.9rem; font-weight: 700; color: var(--slate-700); margin: 1rem 0 0.5rem;">Sector Performance Analysis</h4>';
        html += '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.78rem;">';
        html += '<tr style="background: #f8fafc;"><th style="padding: 0.4rem; text-align: left;">Sector</th><th style="padding: 0.4rem;">Reports</th><th style="padding: 0.4rem;">Verified</th><th style="padding: 0.4rem;">Flagged</th><th style="padding: 0.4rem;">Avg AI Conf</th><th style="padding: 0.4rem;">Resolved</th><th style="padding: 0.4rem;">Avg Resolution (days)</th></tr>';
        Object.entries(data.sector_analysis).forEach(function(entry) {
          var s = entry[1];
          html += '<tr style="border-bottom: 1px solid #e2e8f0;"><td style="padding: 0.3rem; font-weight: 600;">' + s.sector_name + '</td><td style="padding: 0.3rem; text-align: center;">' + s.total_reports + '</td><td style="padding: 0.3rem; text-align: center; color: #10b981;">' + s.verified_genuine + '</td><td style="padding: 0.3rem; text-align: center; color: #ef4444;">' + s.gps_flagged + '</td><td style="padding: 0.3rem; text-align: center;">' + Math.round(s.avg_ai_confidence * 100) + '%</td><td style="padding: 0.3rem; text-align: center;">' + s.resolved + '</td><td style="padding: 0.3rem; text-align: center;">' + s.avg_resolution_days + 'd</td></tr>';
        });
        html += '</table></div>';

        // Anomalies (flagged reports)
        if (data.anomalies && data.anomalies.length > 0) {
          html += '<h4 style="font-size: 0.9rem; font-weight: 700; color: var(--slate-700); margin: 1rem 0 0.5rem;">Anomaly Alerts (' + data.anomalies.length + ')</h4>';
          html += '<div style="max-height: 150px; overflow-y: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.75px;">';
          html += '<tr style="background: #f8fafc;"><th style="padding: 0.3rem; text-align: left;">Ticket</th><th style="padding: 0.3rem; text-align: left;">Title</th><th style="padding: 0.3rem;">AI Conf</th><th style="padding: 0.3rem;">Flag</th></tr>';
          data.anomalies.slice(0, 10).forEach(function(a) {
            html += '<tr style="border-bottom: 1px solid #e2e8f0;"><td style="padding: 0.25rem;">' + a.ticket_number + '</td><td style="padding: 0.25rem;">' + a.title + '</td><td style="padding: 0.25rem; text-align: center;">' + Math.round((a.confidence || 0) * 100) + '%</td><td style="padding: 0.25rem; text-align: center; color: #ef4444;">' + a.verification_status.replace(/_/g, ' ') + '</td></tr>';
          });
          html += '</table></div>';
        }

        content.innerHTML = html;
      })
      .catch(function(err) {
        content.innerHTML = '<div style="color:#ef4444;padding:1rem;"><i class="fa-solid fa-circle-exclamation"></i> ' + (err.message || 'Failed to load analysis') + '</div>';
      });
  }



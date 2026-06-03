/* ==========================================================================
   RISKAI ASSISTANT - CLIENT CORE APPLICATION CONTROLLER
   ========================================================================== */

const API_BASE = "/api";

// Application State
let token = localStorage.getItem("token");
let currentTab = "dashboard";
let selectedCompanyId = null;
let stats = { companies: 0, clauses: 0, assessments: 0 };
let companies = [];

// Initialize Elements
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// App Entrypoint
function initApp() {
    if (token) {
        // Authenticate token
        fetchUserProfile();
    } else {
        showLoginScreen();
    }
}

// Show/Hide Screens
function showLoginScreen() {
    document.getElementById("login-screen").classList.remove("hidden");
    document.getElementById("app").classList.add("hidden");
}

function showMainApp() {
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    
    // Default Tab
    switchTab("dashboard");
    loadStats();
    loadCompanies();
    loadGuidelines();
}

// Fetch Profile Profile
async function fetchUserProfile() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) {
            throw new Error("Token expired or invalid");
        }
        const user = await response.json();
        
        // Update user state
        document.getElementById("user-email").textContent = user.email;
        document.getElementById("user-role").textContent = user.role;
        
        // Handle admin permission views
        const adminSection = document.getElementById("admin-rag-panel");
        if (user.role === "ADMIN") {
            adminSection.classList.remove("hidden");
            document.getElementById("user-role").className = "badge badge-admin";
        } else {
            adminSection.classList.add("hidden");
            document.getElementById("user-role").className = "badge badge-info";
        }
        
        showMainApp();
    } catch (err) {
        console.error(err);
        logout();
    }
}

// Handle Logout
function logout() {
    localStorage.removeItem("token");
    token = null;
    showLoginScreen();
}

// Set active tab
function switchTab(tabId) {
    currentTab = tabId;
    
    // Update navigation styles
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("data-tab") === tabId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
    
    // Update tab visibility
    document.querySelectorAll(".tab-pane").forEach(pane => {
        if (pane.id === `tab-${tabId}`) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });
    
    // Set headers
    const titleEl = document.getElementById("tab-title");
    const subEl = document.getElementById("tab-subtitle");
    
    if (tabId === "dashboard") {
        titleEl.textContent = "Platform Dashboard";
        subEl.textContent = "Real-time credit risk profiles, portfolio exposure, and vector corpus logs.";
        loadStats();
        loadCompanies();
    } else if (tabId === "assessment") {
        titleEl.textContent = "Credit Risk Assessment Portal";
        subEl.textContent = "Submit a prompt or upload financial files to query RAG references and generate reports.";
        populateCompanyDropdowns();
    } else if (tabId === "workshop") {
        titleEl.textContent = "Prompt Tuning Workshop";
        subEl.textContent = "Compare Zero-Shot vs Few-Shot vs Chain-of-Thought (CoT) prompts side-by-side.";
        populateCompanyDropdowns();
    } else if (tabId === "rag") {
        titleEl.textContent = "RAG Guideline Corpus Explorer";
        subEl.textContent = "Query FAISS vector representations and maintain index parameters.";
        loadGuidelines();
    }
}

// ==========================================================================
// EVENT LISTENERS & TRIGGERS
// ==========================================================================
function setupEventListeners() {
    // Navigation items Click
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            switchTab(item.getAttribute("data-tab"));
        });
    });

    // Logout Click
    document.getElementById("logout-btn").addEventListener("click", logout);

    // Login Form Submit
    document.getElementById("login-form").addEventListener("submit", handleLoginSubmit);

    // Modal triggers
    document.getElementById("open-add-company-btn").addEventListener("click", () => {
        document.getElementById("company-modal").classList.remove("hidden");
    });
    document.getElementById("close-company-modal").addEventListener("click", () => {
        document.getElementById("company-modal").classList.add("hidden");
    });
    document.getElementById("cancel-company-btn").addEventListener("click", () => {
        document.getElementById("company-modal").classList.add("hidden");
    });

    // Add Company Form Submit
    document.getElementById("add-company-form").addEventListener("submit", handleAddCompanySubmit);

    // Risk Assessment Report tabs navigation
    document.querySelectorAll(".report-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".report-tab-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const targetPane = btn.getAttribute("data-report-pane");
            document.querySelectorAll(".report-pane").forEach(pane => {
                if (pane.id === `pane-${targetPane}`) {
                    pane.classList.add("active");
                } else {
                    pane.classList.remove("active");
                }
            });
        });
    });

    // Assessment submit
    document.getElementById("assessment-form").addEventListener("submit", handleAssessmentSubmit);

    // Upload statement listener
    document.getElementById("statement-file").addEventListener("change", handleFileSelection);

    // Prompt Workshop compare submit
    document.getElementById("compare-form").addEventListener("submit", handleComparisonSubmit);

    // RAG Ingest Submit
    document.getElementById("rag-ingest-form").addEventListener("submit", handleRAGIngestSubmit);
    
    // RAG Reindex button Click
    document.getElementById("rag-reindex-btn").addEventListener("click", triggerRAGReindexing);

    // RAG Search Input Listener
    document.getElementById("rag-search-input").addEventListener("input", debounce(handleRAGSearchInput, 400));
}

// ==========================================================================
// CORE CRUD & DATA LOADER ROUTINES
// ==========================================================================

// Login Request Form Submit
async function handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const errorMsg = document.getElementById("login-error-msg");
    
    errorMsg.classList.add("hidden");
    
    try {
        const response = await fetch(`${API_BASE}/auth/login/json`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            json: true,
            body: JSON.stringify({ email, password })
        });
        
        if (!response.ok) {
            throw new Error("Invalid username or password");
        }
        
        const data = await response.json();
        token = data.access_token;
        localStorage.setItem("token", token);
        
        // Fetch User and open platform
        fetchUserProfile();
        showToast("Success", "Authentication successful.", "success");
    } catch (err) {
        errorMsg.classList.remove("hidden");
        showToast("Failed", "Login credentials error.", "danger");
    }
}

// Fetch stats counts
async function loadStats() {
    try {
        const authHeader = { "Authorization": `Bearer ${token}` };
        
        const companiesRes = await fetch(`${API_BASE}/companies/`, { headers: authHeader });
        const companyList = await companiesRes.json();
        stats.companies = companyList.length;

        const clausesRes = await fetch(`${API_BASE}/regulatory/`, { headers: authHeader });
        const clauseList = await clausesRes.json();
        stats.clauses = clauseList.length;

        const assessRes = await fetch(`${API_BASE}/assessments/history`, { headers: authHeader });
        const assessList = await assessRes.json();
        stats.assessments = assessList.length;

        // Render dashboard values
        document.getElementById("stat-companies").textContent = stats.companies;
        document.getElementById("stat-clauses").textContent = stats.clauses;
        document.getElementById("stat-assessments").textContent = stats.assessments;
    } catch (e) {
        console.error("Error fetching stats:", e);
    }
}

// Load dynamic list of companies
async function loadCompanies() {
    try {
        const response = await fetch(`${API_BASE}/companies/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        companies = await response.json();
        
        // Populate Company Table
        const tbody = document.getElementById("company-table-body");
        tbody.innerHTML = "";
        
        if (companies.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--color-text-dim);">No companies registered yet.</td></tr>`;
            return;
        }

        for (let comp of companies) {
            // Fetch company risk profile
            const profileRes = await fetch(`${API_BASE}/companies/${comp.id}/risk-profile`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            let profileData = null;
            if (profileRes.ok) {
                profileData = await profileRes.json();
            }

            const tr = document.createElement("tr");
            tr.setAttribute("data-id", comp.id);
            if (selectedCompanyId === comp.id) {
                tr.className = "selected";
            }
            
            const ratingText = profileData ? profileData.risk_rating : "N/A";
            let badgeClass = "badge-info";
            if (ratingText === "LOW") badgeClass = "badge-success";
            else if (ratingText === "MEDIUM") badgeClass = "badge-warning";
            else if (ratingText === "HIGH") badgeClass = "badge-danger";

            tr.innerHTML = `
                <td><strong>${comp.name}</strong></td>
                <td><code class="badge" style="background:rgba(255,255,255,0.03);">${comp.ticker}</code></td>
                <td>${comp.industry}</td>
                <td>${profileData ? profileData.altman_z_score.toFixed(2) : "N/A"}</td>
                <td><span class="badge ${badgeClass}">${ratingText}</span></td>
                <td><button class="btn btn-sm btn-outline inspect-btn">Inspect</button></td>
            `;

            // Inspect Row Click Listener
            tr.addEventListener("click", () => selectCompany(comp.id, profileData, comp));
            tbody.appendChild(tr);
        }
    } catch (e) {
        console.error("Error loading companies:", e);
    }
}

// Select details of a company to render details sidebar
function selectCompany(companyId, profile, company) {
    selectedCompanyId = companyId;
    
    // highlight selected row
    document.querySelectorAll("#company-table-body tr").forEach(tr => {
        if (parseInt(tr.getAttribute("data-id")) === companyId) {
            tr.classList.add("selected");
        } else {
            tr.classList.remove("selected");
        }
    });

    document.getElementById("company-detail-empty").classList.add("hidden");
    const detailContent = document.getElementById("company-detail-content");
    detailContent.classList.remove("hidden");

    // Populate Sidebar Detail Contents
    document.getElementById("detail-company-badge").textContent = company.ticker;
    document.getElementById("detail-name").textContent = company.name;
    document.getElementById("detail-ticker").textContent = company.ticker;
    document.getElementById("detail-industry").textContent = company.industry;

    if (profile) {
        const score = profile.overall_score;
        document.getElementById("detail-risk-score").textContent = score;
        document.getElementById("detail-risk-fill").style.width = `${score}%`;
        
        const rating = profile.risk_rating;
        const ratingEl = document.getElementById("detail-risk-rating");
        ratingEl.textContent = rating;
        
        let rateClass = "badge-info";
        if (rating === "LOW") ratingEl.style.color = "var(--color-emerald)";
        else if (rating === "MEDIUM") ratingEl.style.color = "var(--color-amber)";
        else if (rating === "HIGH") ratingEl.style.color = "var(--color-rose)";
        
        // Ratios
        document.getElementById("ratio-altman").textContent = profile.altman_z_score.toFixed(2);
        document.getElementById("ratio-current").textContent = profile.current_ratio.toFixed(2);
        document.getElementById("ratio-debt").textContent = profile.debt_to_equity.toFixed(2);
        document.getElementById("ratio-coverage").textContent = profile.interest_coverage.toFixed(2);

        // Fill Visual Bars
        // Altman Z-Score fill percentage (capped at 5.0 for UI)
        const altmanPercent = Math.min(Math.max((profile.altman_z_score / 5.0) * 100, 5), 100);
        const fillAltman = document.getElementById("fill-altman");
        fillAltman.style.width = `${altmanPercent}%`;
        fillAltman.className = `ratio-bar-fill ${profile.altman_z_score > 2.9 ? "bg-emerald" : profile.altman_z_score > 1.8 ? "bg-amber" : "bg-rose"}`;

        // Current Ratio fill percentage (capped at 3.0)
        const currentPercent = Math.min(Math.max((profile.current_ratio / 3.0) * 100, 5), 100);
        const fillCurrent = document.getElementById("fill-current");
        fillCurrent.style.width = `${currentPercent}%`;
        fillCurrent.className = `ratio-bar-fill ${profile.current_ratio > 1.5 ? "bg-emerald" : profile.current_ratio > 1.0 ? "bg-amber" : "bg-rose"}`;

        // Debt to Equity fill percentage (high value is bad)
        const debtPercent = Math.min(Math.max((profile.debt_to_equity / 3.0) * 100, 5), 100);
        const fillDebt = document.getElementById("fill-debt");
        fillDebt.style.width = `${debtPercent}%`;
        fillDebt.className = `ratio-bar-fill ${profile.debt_to_equity < 1.0 ? "bg-emerald" : profile.debt_to_equity < 2.0 ? "bg-amber" : "bg-rose"}`;

        // Interest coverage ratio fill percentage (capped at 10.0)
        const coveragePercent = Math.min(Math.max((profile.interest_coverage / 10.0) * 100, 5), 100);
        const fillCoverage = document.getElementById("fill-coverage");
        fillCoverage.style.width = `${coveragePercent}%`;
        fillCoverage.className = `ratio-bar-fill ${profile.interest_coverage > 3.0 ? "bg-emerald" : profile.interest_coverage > 1.5 ? "bg-amber" : "bg-rose"}`;
    } else {
        document.getElementById("detail-risk-score").textContent = "N/A";
        document.getElementById("detail-risk-fill").style.width = "0%";
        document.getElementById("detail-risk-rating").textContent = "NO RATIOS YET";
        document.getElementById("detail-risk-rating").style.color = "var(--color-text-dim)";
        
        // Zero fills
        document.getElementById("ratio-altman").textContent = "N/A";
        document.getElementById("ratio-current").textContent = "N/A";
        document.getElementById("ratio-debt").textContent = "N/A";
        document.getElementById("ratio-coverage").textContent = "N/A";
        
        document.getElementById("fill-altman").style.width = "0%";
        document.getElementById("fill-current").style.width = "0%";
        document.getElementById("fill-debt").style.width = "0%";
        document.getElementById("fill-coverage").style.width = "0%";
    }
}

// Add company submit
async function handleAddCompanySubmit(e) {
    e.preventDefault();
    
    const name = document.getElementById("comp-name").value;
    const ticker = document.getElementById("comp-ticker").value;
    const industry = document.getElementById("comp-industry").value;
    
    // Check if financials are input
    let financial_summary = null;
    const assets = parseFloat(document.getElementById("fin-assets").value);
    if (!isNaN(assets)) {
        financial_summary = {
            total_assets: assets,
            total_liabilities: parseFloat(document.getElementById("fin-liabs").value) || 0,
            current_assets: parseFloat(document.getElementById("fin-cassets").value) || 0,
            current_liabilities: parseFloat(document.getElementById("fin-cliabs").value) || 0,
            retained_earnings: parseFloat(document.getElementById("fin-earnings").value) || 0,
            ebit: parseFloat(document.getElementById("fin-ebit").value) || 0,
            revenue: parseFloat(document.getElementById("fin-revenue").value) || 0,
            market_equity: parseFloat(document.getElementById("fin-equity").value) || 0,
            interest_expense: parseFloat(document.getElementById("fin-interest").value) || 0
        };
    }

    try {
        const response = await fetch(`${API_BASE}/companies/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ name, ticker, industry, financial_summary })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to create company");
        }
        
        document.getElementById("company-modal").classList.add("hidden");
        document.getElementById("add-company-form").reset();
        
        loadCompanies();
        loadStats();
        showToast("Success", `Registered company: ${name}`, "success");
    } catch (e) {
        showToast("Error", e.message, "danger");
    }
}

// Populate target company options in dropdown selects
function populateCompanyDropdowns() {
    const selects = [
        document.getElementById("assess-company"),
        document.getElementById("compare-company")
    ];

    selects.forEach(select => {
        if (!select) return;
        
        // Preserve first "General" option
        const firstOption = select.options[0];
        select.innerHTML = "";
        select.appendChild(firstOption);
        
        companies.forEach(comp => {
            const opt = document.createElement("option");
            opt.value = comp.id;
            opt.textContent = `${comp.name} (${comp.ticker})`;
            select.appendChild(opt);
        });
    });
}

// ==========================================================================
// FINANCIAL STATEMENT UPLOADER
// ==========================================================================
async function handleFileSelection(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const fileLabel = document.querySelector(".file-label span");
    fileLabel.textContent = `Selected: ${file.name}`;
    
    // Create FormData payload
    const formData = new FormData();
    formData.append("file", file);

    showToast("Processing", "Uploading and parsing financial statements...", "success");

    try {
        const response = await fetch(`${API_BASE}/assessments/upload-statement`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Parse failed");
        }

        const res = await response.json();
        
        // Prompt user success
        showToast("Success", `Created/Updated Company ${res.company_name}!`, "success");
        
        // Reload companies and sync stats
        loadCompanies();
        loadStats();
        populateCompanyDropdowns();
        
        // Auto select uploaded company in assess selection
        document.getElementById("assess-company").value = res.company_id;
        
    } catch (e) {
        showToast("File Error", e.message, "danger");
        fileLabel.textContent = "Upload failed. Try another JSON file.";
    }
}

// ==========================================================================
// RISK ASSESSMENT SUBMISSION
// ==========================================================================
async function handleAssessmentSubmit(e) {
    e.preventDefault();
    
    const companyId = document.getElementById("assess-company").value;
    const query = document.getElementById("assess-query").value;
    const variant = document.querySelector('input[name="prompt_variant"]:checked').value;
    const submitBtn = document.getElementById("assess-submit-btn");

    // UI Loading State
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running Analysis...`;
    
    document.getElementById("assessment-result-empty").classList.add("hidden");
    const resultPanel = document.getElementById("assessment-result-content");
    resultPanel.classList.add("hidden");

    try {
        const response = await fetch(`${API_BASE}/assessments/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                company_id: companyId ? parseInt(companyId) : null,
                query: query,
                prompt_variant: variant
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Analysis query request failed");
        }

        const report = await response.json();
        
        // Display report content
        resultPanel.classList.remove("hidden");
        document.getElementById("report-confidence").textContent = `${Math.round(report.confidence_score * 100)}%`;
        document.getElementById("fill-confidence").style.width = `${report.confidence_score * 100}%`;
        document.getElementById("report-text").textContent = report.assessment_text;
        
        // Display Judge details
        document.getElementById("judge-score-acc").textContent = report.judge_accuracy.toFixed(2);
        document.getElementById("judge-score-comp").textContent = report.judge_completeness.toFixed(2);
        document.getElementById("judge-score-align").textContent = report.judge_regulatory_alignment.toFixed(2);
        document.getElementById("judge-feedback-text").textContent = report.judge_feedback;
        
        // Color judge indicators
        document.querySelectorAll(".js-val").forEach(el => {
            const score = parseFloat(el.textContent);
            if (score >= 0.9) el.style.color = "var(--color-emerald)";
            else if (score >= 0.75) el.style.color = "var(--color-amber)";
            else el.style.color = "var(--color-rose)";
        });

        // Display Citations
        const countBadge = document.getElementById("citation-count");
        const listEl = document.getElementById("citations-list");
        listEl.innerHTML = "";
        
        const sources = report.sources || [];
        countBadge.textContent = sources.length;

        if (sources.length === 0) {
            listEl.innerHTML = `<p style="text-align:center;font-size:12px;color:var(--color-text-dim);margin-top:20px;">No RAG citations mapped for this query.</p>`;
        } else {
            sources.forEach(src => {
                const card = document.createElement("div");
                card.className = "citation-card";
                card.innerHTML = `
                    <div class="cite-header">
                        <span class="cite-src">${src.source}</span>
                        <span class="cite-section">${src.section}</span>
                    </div>
                    <p>${src.content}</p>
                `;
                listEl.appendChild(card);
            });
        }
        
        // Auto-switch to risk assessment tab view
        document.querySelector('[data-report-pane="report"]').click();
        showToast("Success", "Risk assessment report generated.", "success");
        loadStats();
    } catch (e) {
        showToast("Failed", e.message, "danger");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Generate Assessment`;
    }
}

// ==========================================================================
// PROMPT TUNING COMPARISON
// ==========================================================================
async function handleComparisonSubmit(e) {
    e.preventDefault();
    
    const companyId = document.getElementById("compare-company").value;
    const query = document.getElementById("compare-query").value;
    const submitBtn = document.getElementById("compare-submit-btn");
    
    const loader = document.getElementById("comparison-loader");
    const resultsContainer = document.getElementById("comparison-results");

    submitBtn.disabled = true;
    loader.classList.remove("hidden");
    resultsContainer.classList.add("hidden");

    try {
        const response = await fetch(`${API_BASE}/assessments/compare`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                company_id: companyId ? parseInt(companyId) : null,
                query: query
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Comparison failed");
        }

        const data = await response.json();
        
        // Map individual result variants
        data.results.forEach(res => {
            const variantSuffix = res.prompt_variant.toLowerCase().replace("_", "");
            
            // Format score percent
            const averageScore = Math.round(((res.judge_accuracy + res.judge_completeness + res.judge_regulatory_alignment) / 3) * 100);
            
            document.getElementById(`comp-score-${variantSuffix}`).textContent = `Judge: ${averageScore}%`;
            document.getElementById(`comp-acc-${variantSuffix}`).textContent = res.judge_accuracy.toFixed(2);
            document.getElementById(`comp-comp-${variantSuffix}`).textContent = res.judge_completeness.toFixed(2);
            document.getElementById(`comp-align-${variantSuffix}`).textContent = res.judge_regulatory_alignment.toFixed(2);
            document.getElementById(`comp-text-${variantSuffix}`).textContent = res.assessment_text;
            document.getElementById(`comp-feedback-${variantSuffix}`).textContent = res.judge_feedback;
        });

        resultsContainer.classList.remove("hidden");
        showToast("Success", "Prompt variations side-by-side ready.", "success");
    } catch (e) {
        showToast("Comparison Error", e.message, "danger");
    } finally {
        submitBtn.disabled = false;
        loader.classList.add("hidden");
    }
}

// ==========================================================================
// RAG INDEX CORPUS ACTIONS
// ==========================================================================
async function loadGuidelines() {
    try {
        const response = await fetch(`${API_BASE}/regulatory/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const references = await response.json();
        
        const container = document.getElementById("guidelines-container");
        const emptyEl = document.getElementById("guidelines-empty");
        
        container.innerHTML = "";
        
        if (references.length === 0) {
            emptyEl.classList.remove("hidden");
            return;
        }
        
        emptyEl.classList.add("hidden");
        references.forEach(ref => {
            const card = document.createElement("div");
            card.className = "rag-corpus-card";
            
            let sourceBadgeClass = "badge-info";
            if (ref.source === "BASEL_III") sourceBadgeClass = "badge-success";
            else if (ref.source === "IFRS_9") sourceBadgeClass = "badge-warning";
            else if (ref.source === "SEC_10K") sourceBadgeClass = "badge-danger";

            card.innerHTML = `
                <div class="rag-corpus-card-header">
                    <div class="rag-corpus-title-row">
                        <span class="badge ${sourceBadgeClass}">${ref.source}</span>
                        <h4>${ref.section}</h4>
                    </div>
                    <span class="help-text">ID: #${ref.id}</span>
                </div>
                <p>${ref.content}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error loading guidelines:", e);
    }
}

// Ingest Guideline Submit
async function handleRAGIngestSubmit(e) {
    e.preventDefault();
    
    const source = document.getElementById("rag-source").value;
    const section = document.getElementById("rag-section").value;
    const content = document.getElementById("rag-content").value;
    const submitBtn = document.getElementById("rag-ingest-btn");

    submitBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/regulatory/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ source, section, content })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Ingest failed");
        }

        document.getElementById("rag-ingest-form").reset();
        loadGuidelines();
        loadStats();
        showToast("Success", "Regulation indexed in FAISS store.", "success");
    } catch (e) {
        showToast("Ingest Error", e.message, "danger");
    } finally {
        submitBtn.disabled = false;
    }
}

// Reindex FAISS vector stores manually
async function triggerRAGReindexing() {
    const btn = document.getElementById("rag-reindex-btn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate fa-spin"></i> Indexing...`;

    try {
        const response = await fetch(`${API_BASE}/regulatory/reindex`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error("Failed to compile FAISS index");
        }

        showToast("Indexed", "FAISS vector store updated successfully.", "success");
    } catch (e) {
        showToast("Failed", e.message, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Reindex FAISS`;
    }
}

// Search input listener
async function handleRAGSearchInput(e) {
    const query = e.target.value.trim();
    if (!query) {
        loadGuidelines();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/regulatory/search?q=${encodeURIComponent(query)}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (!response.ok) throw new Error("Search request failed");
        
        const results = await response.json();
        
        const container = document.getElementById("guidelines-container");
        container.innerHTML = "";
        
        if (results.length === 0) {
            container.innerHTML = `<p style="text-align:center;font-size:12px;color:var(--color-text-dim);margin-top:20px;">No matching vector representations found.</p>`;
            return;
        }

        results.forEach(res => {
            const card = document.createElement("div");
            card.className = "rag-corpus-card";
            card.style.borderColor = "rgba(99, 102, 241, 0.25)";
            
            let sourceBadgeClass = "badge-info";
            if (res.source === "BASEL_III") sourceBadgeClass = "badge-success";
            else if (res.source === "IFRS_9") sourceBadgeClass = "badge-warning";
            else if (res.source === "SEC_10K") sourceBadgeClass = "badge-danger";

            card.innerHTML = `
                <div class="rag-corpus-card-header">
                    <div class="rag-corpus-title-row">
                        <span class="badge ${sourceBadgeClass}">${res.source}</span>
                        <h4>${res.section}</h4>
                    </div>
                    <span class="badge badge-info" style="text-transform:lowercase;font-size:9px;">dist: ${res.score.toFixed(2)}</span>
                </div>
                <p>${res.content}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error executing RAG search:", e);
    }
}

// ==========================================================================
// TOAST MESSAGES UTILITIES
// ==========================================================================
function showToast(title, message, type = "success") {
    const container = document.getElementById("alerts-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    const icon = type === "success" ? "fa-circle-check" : "fa-triangle-exclamation";
    
    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <div>
            <strong>${title}</strong>
            <div style="font-size:10px;font-weight:400;opacity:0.8;">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto remove
    setTimeout(() => {
        toast.style.animation = "slideIn 0.3s reverse forwards";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3500);
}

// Helpers
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} => ${res.status}`);
  return res.json();
}

function endpointForArtifact(id) {
  const map = {
    B1_executive_dashboard: "/api/portfolio/b1",
    B2_trust_dashboard: "/api/portfolio/b2",
    B5_bigquery_dataset: "/api/portfolio/b5",
  };
  return map[id] || null;
}

function readmePathForArtifact(id) {
  const map = {
    B1_executive_dashboard: "B1_executive_dashboard/README.md",
    B2_trust_dashboard: "B2_trust_dashboard/README.md",
    B3_data_model_explorer: "B3_dbt_documentation/README.md",
    B4_airflow_dag: "B4_airflow_dag/README.md",
    B5_bigquery_dataset: "B5_bigquery_dataset/README.md",
    B6_architecture_diagram: "B6_architecture_diagram/README.md",
  };
  return map[id] || `${id}/README.md`;
}

function setSummary(text) {
  const el = document.getElementById("summary");
  el.innerHTML = `<strong>Status:</strong> ${text}`;
}

function showDetail(title, data) {
  document.getElementById("detail-title").textContent = title;
  document.getElementById("detail-json").textContent = JSON.stringify(data, null, 2);
  document.getElementById("detail").classList.remove("hidden");
}

async function buildCards() {
  const manifest = await getJson("/portfolio-assets/manifest.json");
  setSummary(`Loaded ${manifest.artifacts.length} artifacts from manifest.`);

  const cards = document.getElementById("cards");
  cards.innerHTML = "";

  for (const art of manifest.artifacts) {
    const card = document.createElement("article");
    card.className = "card";

    const h3 = document.createElement("h3");
    h3.textContent = `${art.id} — ${art.title}`;
    card.appendChild(h3);

    const q = document.createElement("p");
    q.className = "question";
    q.textContent = art.question || "";
    card.appendChild(q);

    const endpoint = endpointForArtifact(art.id);
    let liveData = null;
    if (endpoint) {
      try {
        liveData = await getJson(endpoint);
      } catch (err) {
        liveData = { _error: err.message };
      }
    }

    if (liveData && !liveData._error) {
      const live = document.createElement("div");
      live.className = "livebox";
      live.innerHTML = `<strong>Live Data (API)</strong>`;

      const lines = summarizePayload(art.id, liveData);
      for (const line of lines) {
        const row = document.createElement("div");
        row.className = "liverow";
        row.textContent = line;
        live.appendChild(row);
      }
      card.appendChild(live);
    } else if (liveData && liveData._error) {
      const err = document.createElement("div");
      err.className = "liveerr";
      err.textContent = `Live API error: ${liveData._error}`;
      card.appendChild(err);
    }

    if (art.visual_asset) {
      const img = document.createElement("img");
      img.src = `/portfolio-assets/${art.visual_asset}`;
      img.alt = `${art.id} visual`;
      card.appendChild(img);
    }

    const actions = document.createElement("div");
    actions.className = "actions";

    const openReadme = document.createElement("a");
    openReadme.className = "linkbtn";
    openReadme.href = `/portfolio-assets/${readmePathForArtifact(art.id)}`;
    openReadme.target = "_blank";
    openReadme.rel = "noopener";
    openReadme.textContent = "Open README";
    actions.appendChild(openReadme);

    if (art.payload) {
      const payloadBtn = document.createElement("button");
      payloadBtn.textContent = "View payload file";
      payloadBtn.onclick = async () => {
        const data = await getJson(`/portfolio-assets/${art.payload}`);
        showDetail(`${art.id} payload file`, data);
      };
      actions.appendChild(payloadBtn);
    }

    if (endpoint) {
      const apiBtn = document.createElement("button");
      apiBtn.textContent = "View live API payload";
      apiBtn.onclick = async () => {
        const data = await getJson(endpoint);
        showDetail(`${art.id} API payload`, data);
      };
      actions.appendChild(apiBtn);
    }

    card.appendChild(actions);
    cards.appendChild(card);
  }
}

function summarizePayload(id, payload) {
  if (id === "B1_executive_dashboard") {
    const out = [];
    out.push(`Updated: ${payload.header?.updated_at || "n/a"} | ${payload.header?.status || ""}`);
    const sections = payload.sections || [];
    for (const sec of sections.slice(0, 3)) {
      const m = (sec.metrics || []).slice(0, 2).map((x) => `${x.label}: ${x.display_value}`).join(" | ");
      out.push(`${sec.title} -> ${m}`);
    }
    return out;
  }

  if (id === "B2_trust_dashboard") {
    const out = [];
    out.push(`Status: ${payload.current_status?.traffic_light || ""} ${payload.current_status?.headline || ""}`);
    for (const m of (payload.trust_vitals || []).slice(0, 4)) {
      out.push(`${m.label}: ${m.display_value}`);
    }
    if (payload.click_audit) {
      out.push(`Click audit: ${payload.click_audit.resolved_count}/${payload.click_audit.resolved_count + payload.click_audit.unresolved_count} (${payload.click_audit.coverage_pct}%)`);
    }
    return out;
  }

  if (id === "B5_bigquery_dataset") {
    const ws = payload.warehouse_summary || {};
    const td = payload.table_details || {};
    return [
      `Table: ${td.table || "n/a"} | Rows: ${td.rows || "n/a"}`,
      `Refresh: ${td.last_refresh || "n/a"} | Health: ${ws.warehouse_health || "n/a"}`,
      `Datasets: ${ws.datasets ?? "n/a"} | Tables: ${ws.tables ?? "n/a"} | Gold: ${ws.gold_models ?? "n/a"}`,
      payload.sample_query?.status || "",
    ].filter(Boolean);
  }

  return [`Artifact: ${payload.artifact || "n/a"}`];
}

document.getElementById("detail-close").addEventListener("click", () => {
  document.getElementById("detail").classList.add("hidden");
});

buildCards().catch((err) => {
  setSummary(`Error loading cockpit: ${err.message}`);
});

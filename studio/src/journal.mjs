/* Session Journal shell. Domain actions remain in the authenticated platform controllers. */
const $ = (id) => document.getElementById(id);
export const element = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">${{ sessions: '<path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/>', agents: '<path d="M8 8h8v8H8zM12 3v5M12 16v5M3 12h5M16 12h5"/>', benches: '<path d="M3 17h18M6 17V7h12v10M9 10h6M9 13h3"/>', sandbox: '<path d="m12 3 9 5v9l-9 5-9-5V8zM3 8l9 5 9-5M12 13v9"/>', evidence: '<path d="M6 3h9l4 4v14H6zM9 11h7M9 15h7M9 18h4"/>', deployments: '<path d="m9 5 11 7-11 7zM4 5v14"/>', connectors: '<path d="M8 3v5M16 3v5M6 8h12v4a6 6 0 0 1-6 6v4M9 18v-1"/>', settings: '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>' }[name]}</svg>`;
const routes = [
  ["sessions", "Session journal"],
  ["agents", "Agents & teams"],
  ["benches", "Benches"],
  ["sandbox", "Sandbox"],
  ["evidence", "Evidence"],
  ["deployments", "Deployments"],
  ["connectors", "Connectors"],
  ["settings", "Workspace settings"],
];
export function mount() {
  const fixture = document.body.dataset.fixture === "true";
  document.body.classList.add("journal-app");
  const product = $("product");
  product.className = "journal-shell";
  const shell = element("div");
  shell.innerHTML = `<aside class="journal-nav" aria-label="Workspace navigation"><a class="journal-brand" href="#/sessions"><span class="mark">CR</span>CertaRig <span class="edition">LAB</span></a><button id="nav-close" aria-label="Close navigation">×</button><button id="palette-open" class="search-trigger">Search workspace <kbd>⌘ K</kbd></button><div id="nav-context"></div><nav aria-label="Destinations">${routes.map(([id, label]) => `<button data-route="${id}">${icon(id)}<span>${label}</span></button>`).join("")}</nav><div class="recent-heading">RECENT SESSIONS <button id="journal-new" aria-label="New session">＋</button></div><div id="recent-sessions"></div><div class="nav-bottom"><span class="connection-dot"></span><span>${fixture ? "Deterministic fixture" : "Local workspace"}</span><a href="/classic" class="classic-link">Classic</a></div></aside><div class="journal-main"><header class="journal-top"><button id="nav-toggle" aria-label="Open navigation">☰</button><div><span id="journal-breadcrumb">Workspace / Session journal</span><span id="journal-mode">Observation only</span></div><div class="header-actions"><button id="journal-refresh" aria-label="Refresh workspace">↻</button><button id="inspector-toggle" aria-label="Open context inspector">Context</button></div></header><div id="global-status"></div><div class="journal-body"><main id="journal-content" tabindex="-1"></main><aside id="context-inspector" aria-label="Context inspector"><div class="inspector-heading"><span>SESSION CONTEXT</span><button id="inspector-close" aria-label="Close context inspector">×</button></div><div class="context-summary"><span id="context-bench">Select a bench</span><h2 id="context-title">Commissioning workspace</h2><p id="context-status">Describe your task to begin.</p></div><div class="context-tabs" role="group" aria-label="Context views"><button data-context="proposal" aria-pressed="true">Proposal</button><button data-context="activity" aria-pressed="false">Activity</button><button data-context="sources" aria-pressed="false">Sources</button></div><div id="context-proposal"></div><div id="context-activity" hidden></div><div id="context-sources" hidden><p>Source observations and raw traces appear here when recorded. No measurements are inferred from a connection.</p></div><div class="context-footnote">Human review governs deployment. Local controllers retain equipment authority.</div></aside></div><footer class="journal-footer"><span id="journal-save-state">Persistent workspace</span><span>${fixture ? "Fixture mode · no equipment access" : "Local Edge · bounded observation"}</span></footer></div>`;
  if (fixture) shell.querySelector(".classic-link").hidden = true;
  const oldGrid = document.querySelector(".workspace-grid");
  const views = {};
  for (const [id, label] of routes) {
    const view = element("section", undefined, "journal-view");
    view.dataset.view = id;
    view.hidden = id !== "sessions";
    if (id !== "sessions") {
      const h = element("div", undefined, "view-heading");
      h.append(element("p", "WORKSPACE", "eyebrow"), element("h1", label));
      view.append(h);
    }
    views[id] = view;
    shell.querySelector("#journal-content").append(view);
  }
  product.prepend(...shell.childNodes);
  const move = (id, target) => target.append($(id));
  const projectBlock = $("project").closest("section"),
    assetBlock = $("asset").closest("section");
  $("nav-context").append(projectBlock, assetBlock);
  move("draft-list", $("recent-sessions"));
  const hero = element("div", undefined, "session-heading");
  hero.innerHTML =
    '<p class="eyebrow">ENGINEERING SESSION</p><h1 id="session-title">Start an engineering session.</h1><p id="session-subtitle">Describe the experiment. Inspect the proposal. Keep the evidence.</p>';
  const next = element("button", "Inspect definition", "primary session-next");
  next.id = "session-next";
  hero.append(next);
  views.sessions.append(hero);
  move("commissioning-chat", views.sessions);
  const proposal = element("section", undefined, "inline-proposal");
  proposal.id = "inline-proposal";
  proposal.innerHTML =
    '<div class="proposal-heading"><span class="eyebrow">PROPOSED DEFINITION</span><button id="open-builder">Edit definition ↗</button></div><h2 id="proposal-title">An agent for your bench</h2><p id="proposal-description">Create a draft or select a saved version to inspect its exact definition.</p><div id="readable-diff"></div><div id="proposal-meta"></div>';
  $("conversation").before(proposal);
  const diffDetails = element("details");
  diffDetails.append(
    element("summary", "Inspect proposed changes"),
    $("readable-diff"),
  );
  $("proposal-meta").before(diffDetails);
  const builder = element("dialog");
  builder.id = "agent-builder";
  builder.setAttribute("aria-labelledby", "builder-title");
  builder.innerHTML =
    '<div class="dialog-heading"><div><p class="eyebrow">AGENT BUILDER</p><h2 id="builder-title">Define the commissioning agent</h2></div><button data-close-dialog aria-label="Close agent builder">×</button></div><div id="builder-content"></div>';
  document.body.append(builder);
  const agentSection = $("agent-form").parentElement;
  const modelSection = $("model-form").closest("details");
  views.settings.append(modelSection);
  $("builder-content").append(agentSection);
  const versionsSection = $("versions").closest("section");
  views.agents.append(versionsSection, $("team-section"));
  views.benches.append($("enrollment"), $("profile-review-panel"));
  const readings = element("section");
  readings.id = "bench-observations";
  readings.innerHTML =
    "<h2>Observed channels</h2><p>Choose a permitted bench to inspect its source data.</p>";
  views.benches.append(readings);
  views.sandbox.append($("sandbox-section"));
  views.evidence.append($("evidence-section"));
  views.deployments.append($("deployment-panel"));
  views.connectors.append($("connector-section"));
  const evaluation = $("qualification").closest("section");
  $("context-proposal").append(evaluation);
  $("context-activity").append($("tasks-section"));
  const profileNotice = element(
    "p",
    "Observation connectivity does not establish physical commissioning. Changes are proposals until installed by a local operator.",
    "scope-note",
  );
  views.benches.append(profileNotice);
  views.settings.append(
    element("h2", "Workspace identity"),
    $("identity"),
    $("scope"),
    $("signout"),
  );
  const newTask = element("button", "New agent", "primary");
  newTask.id = "agents-new";
  newTask.onclick = () => $("new-agent").click();
  views.agents.querySelector(".view-heading").append(newTask);
  const aux = element("div");
  aux.hidden = true;
  aux.id = "compatibility-controls";
  product.append(aux);
  aux.append(oldGrid); // Retain compatibility selectors for the existing controllers.
  aux.append($("refresh"));
  document.querySelector(".workspace-heading")?.remove();
  document.querySelector(".pane-tabs").hidden = true;
  document.querySelector(".inspector-nav").hidden = true;
  document.querySelector("body > .top").hidden = true;
  $("global-status").append($("notice"));
  function context(name) {
    for (const n of ["proposal", "activity", "sources"])
      $("context-" + n).hidden = n !== name;
    document
      .querySelectorAll("[data-context]")
      .forEach((b) =>
        b.setAttribute("aria-pressed", String(b.dataset.context === name)),
      );
  }
  document
    .querySelectorAll("[data-context]")
    .forEach((b) => (b.onclick = () => context(b.dataset.context)));
  let route = "sessions";
  function navigate() {
    const requested = location.hash.replace(/^#\//, "").split("/")[0];
    route = routes.some(([id]) => id === requested) ? requested : "sessions";
    for (const [id, v] of Object.entries(views)) v.hidden = id !== route;
    document.querySelectorAll("[data-route]").forEach((b) => {
      b.setAttribute(
        "aria-current",
        b.dataset.route === route ? "page" : "false",
      );
    });
    $("journal-breadcrumb").textContent =
      `Workspace / ${routes.find(([id]) => id === route)[1]}`;
    product.dataset.currentRoute = route;
    document.body.classList.remove("nav-open");
    document.dispatchEvent(
      new CustomEvent("journalnavigate", { detail: { route } }),
    );
  }
  document.querySelectorAll("[data-route]").forEach(
    (b) =>
      (b.onclick = () => {
        closeDrawers(false);
        location.hash = "/" + b.dataset.route;
      }),
  );
  window.addEventListener("hashchange", navigate);
  navigate();
  function closeDrawers(returnFocus = true) {
    const contextOpen = document.body.classList.contains("context-open");
    const navOpen = document.body.classList.contains("nav-open");
    document.body.classList.remove("nav-open", "context-open");
    $("journal-content").inert = false;
    $("context-inspector").inert = false;
    document.querySelector(".journal-nav").inert = false;
    document.querySelector(".journal-nav").removeAttribute("aria-modal");
    document.querySelector(".journal-nav").removeAttribute("role");
    $("context-inspector").removeAttribute("aria-modal");
    $("context-inspector").removeAttribute("role");
    $("nav-toggle").setAttribute("aria-expanded", "false");
    $("inspector-toggle").setAttribute("aria-expanded", "false");
    if (returnFocus)
      (contextOpen
        ? $("inspector-toggle")
        : navOpen
          ? $("nav-toggle")
          : null
      )?.focus();
  }
  $("nav-toggle").onclick = () => {
    const open = document.body.classList.contains("nav-open");
    closeDrawers(false);
    if (open) return;
    document.body.classList.add("nav-open");
    document.querySelector(".journal-nav").setAttribute("role", "dialog");
    document
      .querySelector(".journal-nav")
      .setAttribute("aria-label", "Workspace navigation");
    document.querySelector(".journal-nav").setAttribute("aria-modal", "true");
    $("journal-content").inert = true;
    $("context-inspector").inert = true;
    $("nav-toggle").setAttribute("aria-expanded", "true");
    $("nav-close").focus();
  };
  $("nav-close").onclick = () => closeDrawers();
  $("inspector-toggle").onclick = () => {
    closeDrawers(false);
    document.body.classList.add("context-open");
    $("journal-content").inert = true;
    document.querySelector(".journal-nav").inert = true;
    $("context-inspector").setAttribute("role", "dialog");
    $("context-inspector").setAttribute("aria-modal", "true");
    $("inspector-toggle").setAttribute("aria-expanded", "true");
    $("inspector-close").focus();
  };
  $("inspector-close").onclick = () => closeDrawers();
  document.addEventListener("journalnavigate", () => closeDrawers(false));
  window.addEventListener("resize", () => closeDrawers(false));
  document.addEventListener("keydown", (e) => {
    const area = document.body.classList.contains("context-open")
      ? $("context-inspector")
      : document.body.classList.contains("nav-open")
        ? document.querySelector(".journal-nav")
        : null;
    if (!area || document.querySelector("dialog[open]")) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeDrawers();
    }
    if (e.key === "Tab") {
      const controls = [
        ...area.querySelectorAll(
          "a[href],button:not(:disabled),select:not(:disabled),input:not(:disabled),textarea:not(:disabled),summary",
        ),
      ].filter((n) => n.getClientRects().length);
      const first = controls[0],
        last = controls.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }
  });
  function openBuilder() {
    builder.showModal();
    $("agent-name").focus();
  }
  $("open-builder").onclick = openBuilder;
  $("session-next").onclick = openBuilder;
  $("new-agent").addEventListener("click", () => {
    location.hash = "/sessions";
    openBuilder();
  });
  $("journal-new").onclick = () => {
    closeDrawers(false);
    location.hash = "/sessions";
    $("new-agent").click();
  };
  $("journal-refresh").onclick = () => $("refresh").click();
  builder.querySelector("[data-close-dialog]").onclick = () => builder.close();
  const palette = element("dialog");
  palette.id = "command-palette";
  palette.setAttribute("aria-labelledby", "palette-title");
  palette.innerHTML =
    '<div class="dialog-heading"><h2 id="palette-title">Find your workspace</h2><button data-close-dialog aria-label="Close search">×</button></div><label for="palette-query">Search destinations</label><input id="palette-query" type="search" autocomplete="off"><div id="palette-results"></div>';
  document.body.append(palette);
  function paletteResults() {
    const q = $("palette-query").value.toLowerCase();
    const items = routes.map(([id, label]) => ({
      label,
      run: () => (location.hash = "/" + id),
    }));
    for (const option of $("asset").options)
      if (option.value && !option.hidden)
        items.push({
          label: `Bench · ${option.textContent}`,
          run: () => {
            if ($("asset").value !== option.value) {
              $("asset").value = option.value;
              $("asset").dispatchEvent(new Event("change"));
            }
            location.hash = "/benches";
          },
        });
    for (const target of $("draft-list").querySelectorAll("button"))
      items.push({
        label: `Session · ${target.textContent}`,
        run: () => {
          location.hash = "/sessions";
          target.click();
        },
      });
    for (const target of $("versions").querySelectorAll("button"))
      items.push({
        label: `Version · ${target.textContent}${target.dataset.versionId ? " · " + target.dataset.versionId.slice(-6) : ""}`,
        run: () => target.click(),
      });
    items.push(
      { label: "New agent", run: () => $("new-agent").click() },
      {
        label: "New project",
        run: () => {
          $("project-form").closest("details").open = true;
          if (innerWidth < 1024) $("nav-toggle").click();
          $("project-name").focus();
        },
      },
      {
        label: "New Sandbox tool",
        run: () => {
          location.hash = "/sandbox";
          $("analysis-form").closest("details").open = true;
          requestAnimationFrame(() => $("analysis-name").focus());
        },
      },
    );
    if ($("spec-title"))
      items.push({
        label: "Describe a bench",
        run: () => {
          location.hash = "/benches";
          requestAnimationFrame(() => $("spec-title").focus());
        },
      });
    const matches = items.filter((item) =>
      item.label.toLowerCase().includes(q),
    );
    $("palette-results").replaceChildren(
      ...matches.slice(0, 30).map((item) => {
        const b = element("button", item.label);
        b.onclick = () => {
          palette.close();
          closeDrawers(false);
          item.run();
        };
        return b;
      }),
    );
    if (!matches.length)
      $("palette-results").append(
        element(
          "p",
          "No permitted destination, bench, session or version matches.",
          "muted",
        ),
      );
  }
  $("palette-open").onclick = () => {
    palette.showModal();
    paletteResults();
    $("palette-query").focus();
  };
  palette.querySelector("[data-close-dialog]").onclick = () => palette.close();
  $("palette-query").oninput = paletteResults;
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      $("palette-open").click();
    }
  });
  const update = () => {
    const title = $("agent-name").value;
    const conversation = $("conversation").children.length > 0;
    const selected = $("version-label").textContent !== "Unsaved draft";
    $("proposal-title").textContent =
      selected || conversation ? title : "An agent for your bench";
    $("context-title").textContent =
      selected || conversation ? title : "Commissioning workspace";
    $("context-bench").textContent =
      $("asset").selectedOptions[0]?.textContent || "No permitted bench";
    $("context-status").textContent = $("version-label").textContent;
    $("journal-save-state").textContent = $("draft-status").textContent;
    $("proposal-description").textContent =
      conversation || selected
        ? "Review the exact instructions, tools and limits. Changes require fresh evaluation."
        : "Create a draft or select a saved version to inspect its exact definition.";
    $("readable-diff").replaceChildren();
    try {
      const raw = JSON.parse($("draft-diff").textContent);
      const diff = Array.isArray(raw) ? raw : [];
      for (const change of diff) {
        const row = element("div", undefined, "diff-row");
        row.append(
          element("strong", change.field.replaceAll("_", " ")),
          element(
            "del",
            change.before === undefined
              ? "Not set"
              : typeof change.before === "string"
                ? change.before
                : JSON.stringify(change.before),
          ),
          element(
            "ins",
            typeof change.after === "string"
              ? change.after
              : JSON.stringify(change.after),
          ),
        );
        $("readable-diff").append(row);
      }
    } catch {
      /* No selected draft. */
    }
    $("session-title").textContent =
      conversation || selected ? title : "Start an engineering session.";
    $("proposal-meta").textContent =
      `${$("version-label").textContent} · ${[...document.querySelectorAll('input[name="tools"]:checked')].length} observation tools · bounded lease`;
  };
  for (const id of [
    "conversation",
    "version-label",
    "draft-status",
    "draft-diff",
  ])
    new MutationObserver(update).observe($(id), {
      childList: true,
      subtree: true,
      characterData: true,
    });
  $("agent-form").addEventListener("input", update);
  document.addEventListener("platformloaded", update);
  document.addEventListener("versionselected", (e) => {
    location.hash = "/sessions/" + e.detail.versionId;
    context("proposal");
  });
  document.addEventListener("journalupdated", () => {
    const strip = $("revoke-strip");
    if (strip && strip.parentElement !== $("global-status"))
      $("global-status").append(strip);
    update();
  });
  return { views, openBuilder, update };
}

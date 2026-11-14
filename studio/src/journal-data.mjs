/* Presentation of authenticated, recorded data. Never creates equipment authority. */
import { element as el } from "./journal.mjs";
const $ = (id) => document.getElementById(id);
export async function init({ api, state, notice, load }) {
  if (!state.me) return;
  let request = 0;
  function sources(result) {
    const host = el("div", undefined, "source-list");
    const rows = result.signals || result.samples || [];
    if (!Array.isArray(rows) || !rows.length) {
      host.append(
        el(
          "p",
          "This connector returned no channel sample list. Inspect the raw source response below.",
        ),
      );
    } else
      for (const sample of rows) {
        const row = el("article");
        row.append(
          el("h3", sample.channel_id || sample.name || "Unidentified channel"),
          el(
            "p",
            `${sample.value ?? "Unknown"} ${sample.unit || "Unknown unit"}`,
          ),
          el(
            "p",
            `Quality: ${sample.stale ? "stale" : sample.quality || "not supplied"} · source timestamp: ${sample.captured_at ?? sample.timestamp ?? "not supplied"}`,
            "muted",
          ),
          el(
            "p",
            `Calibration: ${sample.calibration_id || sample.calibration || "not supplied"}`,
            "muted",
          ),
        );
        host.append(row);
      }
    const details = el("details");
    details.append(
      el("summary", "Inspect raw source response"),
      el("pre", JSON.stringify(result, null, 2)),
    );
    host.append(details);
    return host;
  }
  async function refreshSources() {
    const id = $("asset").value,
      token = ++request;
    const box = $("bench-observations");
    if (!id) {
      box.replaceChildren(
        el("h2", "No permitted bench"),
        el("p", "A Reviewer must enroll a bench and grant observation access."),
      );
      $("context-sources").replaceChildren(el("p", "No permitted source."));
      return;
    }
    try {
      const result = await api(`assets/${id}/signals`);
      if (token !== request || $("asset").value !== id) return;
      box.replaceChildren(el("h2", "Observed channels"), sources(result));
      $("context-sources").replaceChildren(
        el("h2", "Source observations"),
        sources(result),
      );
    } catch (e) {
      if (token !== request) return;
      box.replaceChildren(
        el("h2", "Source unavailable"),
        el("p", e.message, "warn"),
      );
      $("context-sources").replaceChildren(
        el(
          "p",
          "Source unavailable. Earlier readings are not displayed as current.",
          "warn",
        ),
      );
    }
  }
  $("asset").addEventListener("change", refreshSources);
  document.addEventListener("journalnavigate", (e) => {
    if (["benches", "sessions"].includes(e.detail.route)) refreshSources();
  });
  document
    .querySelector("[data-context=sources]")
    .addEventListener("click", refreshSources);
  if (state.me.role === "reviewer") {
    try {
      const result = await api("connectors/registered");
      $("connector").replaceChildren(
        ...result.connectors.map((c) => {
          const o = el("option", `${c.name} · ${c.mode}`);
          o.value = c.id;
          return o;
        }),
      );
      if (!result.connectors.length)
        $("enroll-form").querySelector("button").disabled = true;
    } catch (e) {
      notice(`Connector enrollment unavailable: ${e.message}`, true);
      $("enroll-form").querySelector("button").disabled = true;
    }
  }
  const inspect = $("session-next").onclick;
  const inspectDefinition = () => {
    const version = state.versions.find((v) => v.id === state.selected);
    if (!version?.team_members) {
      inspect();
      return;
    }
    const dialog = el("dialog");
    dialog.setAttribute("aria-label", "Inspect exact team");
    const content = el("div", undefined, "dialog-content");
    content.append(
      el("h2", version.name),
      el(
        "p",
        "Immutable team version. Review exact member definitions and shared limits.",
      ),
    );
    for (const id of version.team_members) {
      const member = state.versions.find((v) => v.id === id);
      content.append(
        el("h3", member ? `${member.name} · v${member.revision}` : id),
        el("p", id, "muted"),
      );
    }
    content.append(
      el(
        "pre",
        JSON.stringify(
          {
            limits: version.limits,
            tools: version.tools,
            member_evaluations: version.member_evaluations,
          },
          null,
          2,
        ),
      ),
    );
    const close = el("button", "Close team inspection");
    close.onclick = () => dialog.close();
    content.append(close);
    dialog.append(content);
    dialog.addEventListener("close", () => dialog.remove(), { once: true });
    document.body.append(dialog);
    dialog.showModal();
    close.focus();
  };
  $("session-next").onclick = inspectDefinition;
  $("open-builder").onclick = inspectDefinition;
  const approve = $("review").onclick;
  $("review").onclick = () => {
    const version = state.versions.find((v) => v.id === state.selected);
    if (!version) return;
    const dialog = el("dialog");
    dialog.setAttribute("aria-labelledby", "review-confirm-title");
    const heading = el("div", undefined, "dialog-heading");
    heading.append(el("h2", "Review exact observation scope"));
    const content = el("div", undefined, "dialog-content");
    const title = el("h2", version.name);
    title.id = "review-confirm-title";
    content.append(
      title,
      el("p", `Version ${version.revision} · ${version.id}`),
      el(
        "p",
        "Observation only. Configuration application and equipment commands remain unavailable.",
      ),
      el(
        "pre",
        JSON.stringify(
          {
            instructions: version.instructions,
            tools: version.tools,
            limits: version.limits,
            team_members: version.team_members || [],
            profile: state.evaluations
              .filter((e) => e.version_id === version.id)
              .at(-1)?.binding,
          },
          null,
          2,
        ),
      ),
    );
    const cancel = el("button", "Keep inspecting");
    cancel.onclick = () => dialog.close();
    const confirm = el(
      "button",
      "Approve exact observation proposal",
      "primary",
    );
    confirm.onclick = () => {
      dialog.close();
      if (state.selected !== version.id) {
        notice(
          "The selected version changed. Inspect the new proposal before review.",
          true,
        );
        return;
      }
      approve();
    };
    content.append(cancel, confirm);
    dialog.append(heading, content);
    dialog.addEventListener("close", () => dialog.remove(), { once: true });
    document.body.append(dialog);
    dialog.showModal();
    cancel.focus();
  };
  document.addEventListener("platformerror", (e) => {
    const { status, path, message } = e.detail;
    if (
      status === 401 ||
      (status === 403 && /session expired|membership/i.test(message))
    ) {
      state.me = null;
      state.runtime = { state: "unknown" };
      state.versions = [];
      state.evaluations = [];
      state.deployments = [];
      $("product").hidden = true;
      $("login").hidden = false;
      $("login").prepend(
        el("p", "Your session is no longer active. Sign in again.", "warn"),
      );
      document.querySelectorAll("dialog[open]").forEach((d) => d.close());
    } else if ([403, 404].includes(status) && /^assets\//.test(path)) {
      state.runtime = { state: "unknown" };
      state.selected = null;
      state.evaluations = [];
      $("context-sources").replaceChildren(
        el(
          "p",
          "Source permission or availability changed. Refresh permitted benches.",
          "warn",
        ),
      );
    }
  });
  document.addEventListener("journalupdated", () => {
    const active = state.deployments.filter((d) =>
      ["running", "approved", "paused"].includes(d.status),
    );
    const strip = $("revoke-strip");
    if (strip) strip.dataset.active = String(active.length > 0);
  });
  // A real read failure never becomes a synthetic measurement or a safe-state claim.
  await refreshSources();
}

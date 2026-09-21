export function renderHero(el) {
  el.innerHTML = `
    <svg class="hero-svg iso-gap" viewBox="0 0 1120 520" role="img" aria-labelledby="heroTitle heroDesc" font-family="Inter Tight, ui-sans-serif, system-ui, sans-serif">
      <title id="heroTitle">Language never crosses into the kernel</title>
      <desc id="heroDesc">
        Agent speech on the left stops at a capability manifest. The right side is ProcessGuardrail:
        five AND terms feeding a single output lamp.
      </desc>
      <rect x="0" y="0" width="1120" height="520" rx="36" fill="#ececef"/>
      <text x="48" y="48" fill="#6e6e73" font-size="13" font-weight="600" letter-spacing="2">AGENT · LANGUAGE</text>
      <g font-size="16" font-weight="500">
        <rect x="48" y="72" width="280" height="44" rx="22" fill="#fff"/>
        <text x="72" y="100" fill="#1d1d1f">“Run the pressure test.”</text>
        <rect x="48" y="128" width="320" height="44" rx="22" fill="#fff"/>
        <text x="72" y="156" fill="#1d1d1f">“Why did the rig stop?”</text>
        <rect x="48" y="184" width="250" height="44" rx="22" fill="#fff"/>
        <text x="72" y="212" fill="#1d1d1f">Narrative only.</text>
      </g>
      <path d="M370 150 H430" stroke="#0071e3" stroke-width="2" stroke-dasharray="6 6"/>
      <polygon points="430,146 442,150 430,154" fill="#0071e3"/>
      <text x="360" y="250" fill="#0071e3" font-size="12" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">stops here</text>

      <rect x="470" y="40" width="18" height="440" rx="4" fill="#0071e3" opacity="0.18"/>
      <rect x="476" y="40" width="6" height="440" rx="3" fill="#0071e3"/>
      <text x="479" y="500" fill="#0071e3" font-size="11" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">manifest</text>

      <rect x="520" y="40" width="560" height="440" rx="28" fill="#0b0b0d"/>
      <text x="548" y="76" fill="rgba(245,245,247,.5)" font-size="13" font-weight="600" letter-spacing="2">KERNEL · ProcessGuardrail</text>
      <text x="548" y="102" fill="#f5f5f7" font-size="22" font-weight="600">Numbers decide. The model does not get a vote.</text>

      <g font-size="14" fill="#f5f5f7" font-family="IBM Plex Mono, ui-monospace">
        <rect class="cell" x="548" y="130" width="300" height="44" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="152" r="5" fill="#1d7a46"/>
        <text x="584" y="157">actuation enabled</text>

        <rect x="548" y="184" width="300" height="44" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="206" r="5" fill="#1d7a46"/>
        <text x="584" y="211">permit requested</text>

        <rect x="548" y="238" width="300" height="44" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="260" r="5" fill="#1d7a46"/>
        <text x="584" y="265">trip not latched</text>

        <rect x="548" y="292" width="300" height="44" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="314" r="5" fill="#1d7a46"/>
        <text x="584" y="319">e-stop closed</text>

        <rect x="548" y="346" width="300" height="44" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="368" r="5" fill="#1d7a46"/>
        <text x="584" y="373">process healthy</text>
      </g>

      <path d="M848 152 H910 V368 H848" fill="none" stroke="#0071e3" stroke-width="2"/>
      <rect x="910" y="236" width="44" height="48" fill="#0071e3"/>
      <text x="932" y="222" fill="rgba(245,245,247,.55)" font-size="11" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">AND</text>
      <circle cx="996" cy="260" r="22" fill="#1d7a46"/>
      <text x="996" y="312" fill="#f5f5f7" font-size="13" font-weight="600" text-anchor="middle">OUTPUT</text>
      <text x="548" y="440" fill="rgba(245,245,247,.45)" font-size="13">Language never crosses this gap. GPIO is not a chat completion.</text>
    </svg>
  `;
}

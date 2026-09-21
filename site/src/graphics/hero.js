export function renderHero(el) {
  el.innerHTML = `
    <svg class="hero-svg iso-gap" viewBox="0 0 1120 460" role="img" aria-labelledby="heroTitle heroDesc" font-family="Inter Tight, ui-sans-serif, system-ui, sans-serif">
      <title id="heroTitle">Language never crosses into the kernel</title>
      <desc id="heroDesc">
        Agent speech on the left stops at a capability manifest. The right side is ProcessGuardrail:
        five AND terms feeding a single output lamp.
      </desc>
      <rect x="0" y="0" width="1120" height="460" rx="32" fill="#ececef"/>
      <text x="40" y="40" fill="#6e6e73" font-size="13" font-weight="600" letter-spacing="2">AGENT · LANGUAGE</text>
      <g font-size="16" font-weight="500">
        <rect x="40" y="60" width="280" height="40" rx="20" fill="#fff"/>
        <text x="64" y="86" fill="#1d1d1f">“Run the pressure test.”</text>
        <rect x="40" y="110" width="320" height="40" rx="20" fill="#fff"/>
        <text x="64" y="136" fill="#1d1d1f">“Why did the rig stop?”</text>
        <rect x="40" y="160" width="250" height="40" rx="20" fill="#fff"/>
        <text x="64" y="186" fill="#1d1d1f">Narrative only.</text>
      </g>
      <path d="M360 130 H430" stroke="#0071e3" stroke-width="2" stroke-dasharray="6 6"/>
      <polygon points="430,126 442,130 430,134" fill="#0071e3"/>
      <text x="350" y="220" fill="#0071e3" font-size="12" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">stops here</text>

      <rect x="470" y="28" width="18" height="404" rx="4" fill="#0071e3" opacity="0.18"/>
      <rect x="476" y="28" width="6" height="404" rx="3" fill="#0071e3"/>
      <text x="479" y="448" fill="#0071e3" font-size="11" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">manifest</text>

      <rect x="520" y="28" width="560" height="404" rx="24" fill="#0b0b0d"/>
      <text x="548" y="60" fill="rgba(245,245,247,.5)" font-size="13" font-weight="600" letter-spacing="2">KERNEL · ProcessGuardrail</text>
      <text x="548" y="86" fill="#f5f5f7" font-size="20" font-weight="600">Numbers decide. The model does not get a vote.</text>

      <g font-size="14" fill="#f5f5f7" font-family="IBM Plex Mono, ui-monospace">
        <rect class="cell" x="548" y="108" width="300" height="40" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="128" r="5" fill="#1d7a46"/>
        <text x="584" y="133">actuation enabled</text>

        <rect x="548" y="156" width="300" height="40" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="176" r="5" fill="#1d7a46"/>
        <text x="584" y="181">permit requested</text>

        <rect x="548" y="204" width="300" height="40" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="224" r="5" fill="#1d7a46"/>
        <text x="584" y="229">trip not latched</text>

        <rect x="548" y="252" width="300" height="40" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="272" r="5" fill="#1d7a46"/>
        <text x="584" y="277">e-stop closed</text>

        <rect x="548" y="300" width="300" height="40" rx="10" fill="#111114" stroke="#1d7a46"/>
        <circle cx="568" cy="320" r="5" fill="#1d7a46"/>
        <text x="584" y="325">process healthy</text>
      </g>

      <path d="M848 128 H910 V320 H848" fill="none" stroke="#0071e3" stroke-width="2"/>
      <rect x="910" y="200" width="44" height="48" fill="#0071e3"/>
      <text x="932" y="186" fill="rgba(245,245,247,.55)" font-size="11" font-family="IBM Plex Mono, ui-monospace" text-anchor="middle">AND</text>
      <circle cx="996" cy="224" r="22" fill="#1d7a46"/>
      <text x="996" y="274" fill="#f5f5f7" font-size="13" font-weight="600" text-anchor="middle">OUTPUT</text>
      <text x="548" y="392" fill="rgba(245,245,247,.45)" font-size="13">Language never crosses this gap. GPIO is not a chat completion.</text>
    </svg>
  `;
}

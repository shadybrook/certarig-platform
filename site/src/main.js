import { renderHero } from "./graphics/hero.js";
import { renderLoop } from "./graphics/loop.js";
import { renderKernel } from "./graphics/kernel.js";
import { renderZip } from "./graphics/zip.js";

renderHero(document.querySelector("#hero-graphic"));
renderLoop(document.querySelector("#loop-graphic"));
renderKernel(document.querySelector("#kernel-graphic"));
renderZip(document.querySelector("#zip-graphic"));

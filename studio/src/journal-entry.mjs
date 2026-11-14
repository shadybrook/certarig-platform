import { mount } from "./journal.mjs";
const journal = mount();
if (document.body.dataset.fixture === "true") {
  const { init } = await import("./journal-fixture.mjs");
  init(journal);
} else {
  const platform = await import("./platform.mjs");
  const { init } = await import("./journal-data.mjs");
  await init(platform);
  if (platform.state.me) {
    const specs = await import("./bench-specs.mjs");
    specs.init(platform);
  }
}

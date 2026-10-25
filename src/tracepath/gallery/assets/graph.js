// The answer graph of the gallery page (spec 0011): places, draws and selects.
// Every item's state is decided by the build and read from its data block;
// this script decides nothing about an item.
(function () {
  "use strict";

  if (typeof HTMLDialogElement !== "function" || typeof d3 === "undefined") return;
  const dialog = document.querySelector("dialog.gw");
  if (!dialog) return;

  const SVG = "http://www.w3.org/2000/svg";
  const TICKS = 300; // d3's own cooling schedule
  const PAD = 28; // pixels kept clear around the fitted graph
  const CLICK = 4; // pointer travel under this many pixels is a click
  const ROOT_PI = Math.sqrt(Math.PI); // a square of side r * ROOT_PI has a dot's area
  const HELD_GAP = Number(dialog.dataset.heldGap);
  const RING_GAP = Number(dialog.dataset.ringGap);

  const canvas = dialog.querySelector(".gw-canvas");
  const linkLayer = canvas.querySelector(".gw-links");
  const nodeLayer = canvas.querySelector(".gw-nodes");
  const heading = dialog.querySelector(".gw-heading");
  const panel = dialog.querySelector(".gw-panel");
  const closeButton = dialog.querySelector("[data-gw=close]");
  const toggle = dialog.querySelector("[data-gw=switch]");

  const buttons = new Map(); // slug to its Graph button
  const laid = new Map(); // slug to its parsed graph and positions
  let state = null; // the open graph

  function element(name, attributes, text) {
    const node = document.createElementNS(SVG, name);
    for (const key in attributes) node.setAttribute(key, attributes[key]);
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function html(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // An item's outline grown by `gap`: a square for an unresolved name, else a circle.
  function outline(item, gap, className) {
    if (item.unresolved) {
      const half = (item.radius * ROOT_PI) / 2 + gap;
      return element("rect", {
        class: className, x: -half, y: -half, width: 2 * half, height: 2 * half,
      });
    }
    return element("circle", { class: className, r: item.radius + gap });
  }

  // Run d3-force to the end before anything is drawn, around (0, 0).
  function layout(graph) {
    const nodes = graph.items.map((item) => ({ id: item.id, radius: item.radius }));
    const links = graph.links
      .filter((link) => link.drawn)
      .map((link) => ({ source: link.source, target: link.target }));
    const simulation = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((node) => node.id).distance(40))
      .force("charge", d3.forceManyBody().strength(-60))
      .force("collide", d3.forceCollide((node) => node.radius + 2))
      .force("x", d3.forceX(0).strength(0.06))
      .force("y", d3.forceY(0).strength(0.06))
      .stop();
    for (let tick = 0; tick < TICKS; tick += 1) simulation.tick();
    return new Map(nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
  }

  // The view that puts every dot inside the canvas (AC-25).
  function fitted() {
    const box = canvas.getBoundingClientRect();
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const point of state.positions.values()) {
      minX = Math.min(minX, point.x);
      maxX = Math.max(maxX, point.x);
      minY = Math.min(minY, point.y);
      maxY = Math.max(maxY, point.y);
    }
    const scale = Math.max(
      0.01,
      Math.min(
        4,
        (box.width - 2 * PAD) / Math.max(maxX - minX, 1),
        (box.height - 2 * PAD) / Math.max(maxY - minY, 1)
      )
    );
    return {
      k: scale,
      x: box.width / 2 - (scale * (minX + maxX)) / 2,
      y: box.height / 2 - (scale * (minY + maxY)) / 2,
    };
  }

  function screen(id) {
    const point = state.positions.get(id);
    return { x: state.view.x + state.view.k * point.x, y: state.view.y + state.view.k * point.y };
  }

  function place() {
    for (const [id, node] of state.nodes) {
      const at = screen(id);
      node.setAttribute("transform", "translate(" + at.x + " " + at.y + ")");
    }
    state.lines.forEach((line, number) => {
      const link = state.graph.links[number];
      const from = screen(link.source);
      const to = screen(link.target);
      // End at the target's edge, so an arrowhead sits outside the dot.
      const target = state.byId.get(link.target);
      const gap = target.radius + (target.held ? HELD_GAP + 1.5 : 1.5);
      const length = Math.hypot(to.x - from.x, to.y - from.y) || 1;
      const cut = Math.min(gap, length) / length;
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x - (to.x - from.x) * cut);
      line.setAttribute("y2", to.y - (to.y - from.y) * cut);
    });
  }

  function draw() {
    linkLayer.replaceChildren();
    nodeLayer.replaceChildren();
    state.nodes = new Map();
    state.items = new Map();
    state.lines = new Map();
    state.byId = new Map(state.graph.items.map((item) => [item.id, item]));
    state.graph.links.forEach((link, number) => {
      if (!link.drawn) return;
      const line = element("line", { class: link.held ? "gw-link is-held" : "gw-link" });
      line.append(element("title", {}, link.source + " " + link.type + " " + link.target));
      linkLayer.append(line);
      state.lines.set(number, line);
    });
    for (const item of state.graph.items) {
      const classes = ["gw-node", item.cited ? "is-cited" : "is-other"];
      if (item.held) classes.push("is-held");
      if (item.unresolved) classes.push("is-unresolved");
      const node = element("g", { class: classes.join(" ") });
      node.append(outline(item, 0, "gw-dot"));
      if (item.held) node.append(outline(item, HELD_GAP, "gw-held"));
      node.append(outline(item, RING_GAP, "gw-ring"));
      node.append(element("text", { class: "gw-label", x: item.radius + 5, y: 3 }, item.id));
      node.append(element("title", {}, item.id + " · " + item.type));
      node.addEventListener("pointerenter", () => node.classList.add("is-hover"));
      node.addEventListener("pointerleave", () => node.classList.remove("is-hover"));
      nodeLayer.append(node);
      state.nodes.set(item.id, node);
      state.items.set(node, item);
    }
    place();
  }

  function itemAt(target) {
    for (let node = target; node && node !== canvas; node = node.parentNode) {
      if (state.items.has(node)) return state.items.get(node);
    }
    return null;
  }

  // Ring the selection and dim all but it, its neighbours and its own links (AC-34).
  function select(item) {
    state.selected = item;
    const near = new Set(item === null ? [] : item.neighbours);
    for (const [id, node] of state.nodes) {
      const chosen = item !== null && id === item.id;
      node.classList.toggle("is-selected", chosen);
      node.classList.toggle("is-near", near.has(id));
      node.classList.toggle("is-dim", item !== null && !chosen && !near.has(id));
    }
    state.lines.forEach((line, number) => {
      const link = state.graph.links[number];
      const own = item !== null && (link.source === item.id || link.target === item.id);
      line.classList.toggle("is-active", own);
      line.classList.toggle("is-dim", item !== null && !own);
      if (own) line.setAttribute("marker-end", "url(#gw-arrow)");
      else line.removeAttribute("marker-end");
    });
    if (item === null) showAnswer();
    else showItem(item);
  }

  // Hide every item neither cited nor next to a cited one, and their lines (AC-30, AC-31).
  function filter(on) {
    toggle.checked = on;
    for (const [id, node] of state.nodes) {
      node.classList.toggle("is-out", on && !state.byId.get(id).near_cited);
    }
    state.lines.forEach((line, number) => {
      const link = state.graph.links[number];
      const out = !state.byId.get(link.source).near_cited || !state.byId.get(link.target).near_cited;
      line.classList.toggle("is-out", on && out);
    });
    if (on && state.selected !== null && !state.selected.near_cited) select(null);
  }

  function showAnswer() {
    const parts = [html("p", "gw-eyebrow", state.graph.label), html("h2", "gw-title", "Answer")];
    if (state.graph.cited_count === 0) {
      parts.push(html("p", "gw-empty", "This answer cites no item."));
    }
    panel.replaceChildren(...parts);
  }

  function showItem(item) {
    panel.replaceChildren(html("p", "gw-eyebrow", item.type), html("h2", "gw-title", item.id));
  }

  function open(slug) {
    let found = laid.get(slug);
    if (!found) {
      const graph = JSON.parse(document.getElementById("graph-" + slug).textContent);
      found = { graph: graph, positions: layout(graph) };
      laid.set(slug, found);
    }
    state = { slug: slug, graph: found.graph, positions: found.positions, selected: null };
    heading.textContent = found.graph.label;
    if (!dialog.open) dialog.showModal();
    state.view = fitted();
    draw();
    toggle.disabled = found.graph.cited_count === 0;
    filter(false);
    select(null);
    closeButton.focus();
  }

  let down = null;
  canvas.addEventListener("pointerdown", (event) => {
    down = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener("pointerup", (event) => {
    if (down === null) return;
    const moved = Math.hypot(event.clientX - down.x, event.clientY - down.y);
    down = null;
    if (moved < CLICK) select(itemAt(event.target));
  });

  toggle.addEventListener("change", () => filter(toggle.checked));
  closeButton.addEventListener("click", () => dialog.close());
  // Esc, the close button and a back gesture all end here (AC-6).
  dialog.addEventListener("close", () => {
    const button = state && buttons.get(state.slug);
    if (button) button.focus();
  });
  window.addEventListener("resize", () => {
    if (!dialog.open || state === null) return;
    state.view = fitted();
    place();
  });

  for (const button of document.querySelectorAll("button[data-graph]")) {
    buttons.set(button.dataset.graph, button);
    button.addEventListener("click", () => open(button.dataset.graph));
    button.hidden = false;
  }
})();

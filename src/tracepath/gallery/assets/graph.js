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

  const canvas = dialog.querySelector(".gw-canvas");
  const linkLayer = canvas.querySelector(".gw-links");
  const nodeLayer = canvas.querySelector(".gw-nodes");
  const heading = dialog.querySelector(".gw-heading");
  const panel = dialog.querySelector(".gw-panel");
  const closeButton = dialog.querySelector("[data-gw=close]");

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
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x);
      line.setAttribute("y2", to.y);
    });
  }

  function draw() {
    linkLayer.replaceChildren();
    nodeLayer.replaceChildren();
    state.nodes = new Map();
    state.items = new Map();
    state.lines = new Map();
    state.graph.links.forEach((link, number) => {
      if (!link.drawn) return;
      const line = element("line", { class: "gw-link" });
      line.append(element("title", {}, link.source + " " + link.type + " " + link.target));
      linkLayer.append(line);
      state.lines.set(number, line);
    });
    for (const item of state.graph.items) {
      const node = element("g", { class: "gw-node" });
      node.append(element("circle", { class: "gw-dot", r: item.radius }));
      node.append(element("title", {}, item.id + " · " + item.type));
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

  function select(item) {
    state.selected = item;
    for (const [id, node] of state.nodes) {
      node.classList.toggle("is-selected", item !== null && id === item.id);
    }
    if (item === null) showAnswer();
    else showItem(item);
  }

  function showAnswer() {
    panel.replaceChildren(html("p", "gw-eyebrow", state.graph.label), html("h2", "gw-title", "Answer"));
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

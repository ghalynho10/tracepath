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
  const LABEL_GAP = 5; // pixels between a dot's edge and its label
  const CLICK = 4; // pointer travel under this many pixels is a click
  const REACH = 12; // a press acts on the nearest dot centre this close, in pixels
  const TOUCH_REACH = 20; // the same, for a finger
  const STEP = 1.25; // one press of a zoom button
  const ZOOM_OUT = 0.5; // the view zooms from half the fitted scale
  const ZOOM_IN = 6; // to six times it
  const WARM = 0.3; // how lively the graph stays while a dot is dragged
  const STILL = window.matchMedia("(prefers-reduced-motion: reduce)");
  const ROOT_PI = Math.sqrt(Math.PI); // a square of side r * ROOT_PI has a dot's area
  const HELD_GAP = Number(dialog.dataset.heldGap);
  const RING_GAP = Number(dialog.dataset.ringGap);

  const canvas = dialog.querySelector(".gw-canvas");
  const linkLayer = canvas.querySelector(".gw-links");
  const nodeLayer = canvas.querySelector(".gw-nodes");
  const heading = dialog.querySelector("#gw-heading");
  const counter = dialog.querySelector(".gw-count");
  const previousButton = dialog.querySelector("[data-gw=previous]");
  const nextButton = dialog.querySelector("[data-gw=next]");
  const panel = dialog.querySelector(".gw-panel");
  const closeButton = dialog.querySelector("[data-gw=close]");
  const toggle = dialog.querySelector("[data-gw=switch]");
  const foot = dialog.querySelector(".gw-foot");
  const keyToggle = dialog.querySelector("[data-gw=key]");
  const zoomStrip = dialog.querySelector(".gw-zoom");

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

  // The one set of forces, for the layout and for dragging a dot.
  function simulate(graph, nodes) {
    const links = graph.links
      .filter((link) => link.drawn)
      .map((link) => ({ source: link.source, target: link.target }));
    return d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((node) => node.id).distance(40))
      .force("charge", d3.forceManyBody().strength(-60))
      .force("collide", d3.forceCollide((node) => node.radius + 2))
      .force("x", d3.forceX(0).strength(0.06))
      .force("y", d3.forceY(0).strength(0.06))
      .stop();
  }

  // Run d3-force to the end before anything is drawn, around (0, 0).
  function layout(graph) {
    const nodes = graph.items.map((item) => ({ id: item.id, radius: item.radius }));
    const simulation = simulate(graph, nodes);
    for (let tick = 0; tick < TICKS; tick += 1) simulation.tick();
    return new Map(nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
  }

  // A copy of the standard layout, so a dragged dot never moves the cached one and every
  // open starts from the same places (AC-76).
  function standard(positions) {
    return new Map([...positions].map(([id, point]) => [id, { x: point.x, y: point.y }]));
  }

  // The live simulation a dragged dot runs, made on the first drag of this open.
  function live() {
    if (!state.live) {
      const nodes = state.graph.items.map((item) => {
        const point = state.positions.get(item.id);
        return { id: item.id, radius: item.radius, x: point.x, y: point.y };
      });
      state.live = simulate(state.graph, nodes).on("tick", () => {
        for (const node of nodes) state.positions.set(node.id, { x: node.x, y: node.y });
        place();
      });
      state.liveNodes = new Map(nodes.map((node) => [node.id, node]));
    }
    return state.live;
  }

  function stopLive() {
    if (state && state.live) state.live.stop();
  }

  // The view that puts every dot inside the canvas (AC-25), above the zoom buttons (AC-93).
  function fitted() {
    const box = canvas.getBoundingClientRect();
    const bottom = Math.max(PAD, box.bottom - zoomStrip.getBoundingClientRect().top + PAD / 2);
    const height = box.height - PAD - bottom;
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
        height / Math.max(maxY - minY, 1)
      )
    );
    return {
      k: scale,
      x: box.width / 2 - (scale * (minX + maxX)) / 2,
      y: PAD + height / 2 - (scale * (minY + maxY)) / 2,
    };
  }

  function screen(id) {
    const point = state.positions.get(id);
    return { x: state.view.x + state.view.k * point.x, y: state.view.y + state.view.k * point.y };
  }

  function place() {
    state.tree = null; // the dots moved, so the nearest dot search is rebuilt
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
    arrangeLabels();
  }

  // Each label's width, in the label's own font, measured once per open.
  const measure = document.createElement("canvas").getContext("2d");
  function measureLabels() {
    const first = state.labels.values().next().value;
    if (!first) return;
    const style = getComputedStyle(first.text);
    measure.font = style.fontWeight + " " + style.fontSize + " " + style.fontFamily;
    for (const [id, label] of state.labels) label.width = measure.measureText(id).width;
  }

  // The longest start of `id` that fits `room` pixels with "…" after it.
  function shortened(id, room) {
    let low = 0;
    let high = id.length;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      if (measure.measureText(id.slice(0, mid) + "…").width <= room) low = mid;
      else high = mid - 1;
    }
    return id.slice(0, low) + "…";
  }

  // A label that would cross the canvas's right edge sits left of its dot when there is
  // more room there (AC-88), and one that fits on neither side is shortened with "…"
  // (AC-87). Where cited labels overlap, the one cited first keeps its label and the
  // others show theirs only when hovered, selected or next to the selection (AC-89, AC-90).
  function arrangeLabels() {
    const width = canvas.getBoundingClientRect().width;
    const shown = [];
    const cited = [];
    for (const item of state.graph.items) {
      const label = state.labels.get(item.id);
      const at = screen(item.id);
      const room = at.x - item.radius - LABEL_GAP - 2; // to the left of the dot
      const right = width - 2 - (at.x + item.radius + LABEL_GAP);
      const left = label.width > right && room > right;
      if (left !== label.left) {
        label.left = left;
        const shift = item.radius + LABEL_GAP;
        label.text.setAttribute("x", left ? -shift : shift);
        label.text.setAttribute("text-anchor", left ? "end" : "start");
      }
      const space = Math.max(room, right);
      const words = label.width > space ? shortened(item.id, space) : item.id;
      if (words !== label.text.textContent) label.text.textContent = words;
      if (!item.cited) continue;
      const drawn = Math.min(label.width, space);
      const offset = item.radius + LABEL_GAP;
      const start = left ? at.x - offset - drawn : at.x + offset;
      cited.push({ item: item, box: [start, at.y - 7, start + drawn, at.y + 4] });
    }
    cited.sort((a, b) => a.item.cite_order - b.item.cite_order);
    for (const { item, box } of cited) {
      const crowded = shown.some(
        (other) => box[0] < other[2] && other[0] < box[2] && box[1] < other[3] && other[1] < box[3]
      );
      state.nodes.get(item.id).classList.toggle("is-crowded", crowded);
      if (!crowded) shown.push(box);
    }
  }

  function draw() {
    hover(null);
    linkLayer.replaceChildren();
    nodeLayer.replaceChildren();
    state.nodes = new Map();
    state.labels = new Map();
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
      const text = element("text", { class: "gw-label", x: item.radius + LABEL_GAP, y: 3 });
      text.textContent = item.id;
      node.append(text);
      state.labels.set(item.id, { text: text, left: false, width: 0 });
      node.append(element("title", {}, item.id + " · " + item.type));
      nodeLayer.append(node);
      state.nodes.set(item.id, node);
    }
    measureLabels();
    place();
  }

  // The item whose dot centre is nearest the pointer and within reach, among the dots the
  // switch shows, or null; the drawings stay small, the reach does not (AC-84 to AC-86).
  function nearest(event) {
    if (!state.tree) {
      const shown = state.graph.items.filter(
        (item) => !state.nodes.get(item.id).classList.contains("is-out")
      );
      state.tree = d3
        .quadtree()
        .x((item) => screen(item.id).x)
        .y((item) => screen(item.id).y)
        .addAll(shown);
    }
    const box = canvas.getBoundingClientRect();
    const reach = event.pointerType === "touch" ? TOUCH_REACH : REACH;
    const found = state.tree.find(event.clientX - box.left, event.clientY - box.top, reach);
    return found === undefined ? null : found;
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
    state.tree = null;
    for (const [id, node] of state.nodes) {
      node.classList.toggle("is-out", on && !state.byId.get(id).near_cited);
    }
    state.lines.forEach((line, number) => {
      const link = state.graph.links[number];
      const out =
        !state.byId.get(link.source).near_cited || !state.byId.get(link.target).near_cited;
      line.classList.toggle("is-out", on && out);
    });
    if (on && state.selected !== null && !state.selected.near_cited) select(null);
  }

  // A selection made in the panel: shown even if the switch hid it, and centred
  // without changing the scale (AC-40).
  function choose(item) {
    if (toggle.checked && !item.near_cited) filter(false);
    select(item);
    const box = canvas.getBoundingClientRect();
    const point = state.positions.get(item.id);
    state.view.x = box.width / 2 - state.view.k * point.x;
    state.view.y = box.height / 2 - state.view.k * point.y;
    place();
    focusTitle();
  }

  function focusTitle() {
    panel.querySelector(".gw-title").focus({ preventScroll: true });
  }

  // Stored text drawn from the runs the build made (spec 0012): one element per run, by
  // textContent; flag 1 is code, 2 bold. A code run holds one `w` element per word, the
  // spaces kept as text between them (AC-96). No runs means plain text (AC-98, AC-101).
  function formatted(node, text, runs) {
    if (!runs) {
      node.textContent = text;
      return node;
    }
    for (const [words, flags] of runs) {
      let part = document.createTextNode(words);
      if (flags & 1) {
        part = html("code");
        for (const piece of words.split(/( +)/)) {
          if (/^ +$/.test(piece)) part.append(piece);
          else if (piece) part.append(html("span", "w", piece));
        }
      }
      if (flags & 2) {
        const strong = html("strong");
        strong.append(part);
        part = strong;
      }
      node.append(part);
    }
    return node;
  }

  // An id that selects its item when clicked; the id goes in a data attribute only.
  function idButton(id) {
    const button = html("button", "gw-id", id);
    button.type = "button";
    button.dataset.item = id;
    return button;
  }

  function title(text) {
    const node = html("h2", "gw-title", text);
    node.tabIndex = -1;
    return node;
  }

  function itemList(heading, items) {
    if (items.length === 0) return [];
    const list = html("ul", "gw-list");
    for (const item of items) {
      const row = html("li");
      row.append(idButton(item.id), " " + item.type);
      list.append(row);
    }
    return [html("h3", "gw-sub", heading + " (" + items.length + ")"), list];
  }

  // The answer view: the entry's own question, verdict and claims from the list on the
  // page, so their labels cannot differ (AC-36 to AC-38), then every item (AC-52).
  function showAnswer() {
    const view = html("div", "gw-answer");
    view.append(html("p", "gw-eyebrow", state.graph.label), title("Answer"));
    if (state.graph.cited_count === 0) {
      view.append(html("p", "gw-empty", "This answer cites no item."));
    }
    for (const part of [".question", ".verdict", "ol"]) {
      const found = state.article.querySelector(":scope > " + part);
      if (found) view.append(found.cloneNode(true));
    }
    if (!state.article.querySelector(":scope > ol")) view.append(html("p", "", "No claims."));
    view.append(
      ...itemList("Cited", state.graph.items.filter((item) => item.cited)),
      ...itemList("Not cited", state.graph.items.filter((item) => !item.cited))
    );
    panel.replaceChildren(view);
    panel.scrollTop = 0;
  }

  function twoDigits(number) {
    return String(number).padStart(2, "0");
  }

  // The item view, filled with textContent only, so stored text stays text (AC-42 to AC-53).
  function showItem(item) {
    const back = html("button", "gw-back", "Back to the answer");
    back.type = "button";
    back.addEventListener("click", () => {
      select(null);
      focusTitle();
    });
    const words = [item.type];
    if (item.held) words.push("HELD");
    if (item.marker) words.push(item.marker);
    if (item.unresolved) words.push("UNRESOLVED NAME");
    const where = html("p", "gw-meta");
    if (item.source) {
      // A new tab, so the open graph survives the visit to JobHunt (AC-103).
      const link = html("a", "", item.location);
      link.href = item.source;
      link.target = "_blank";
      link.rel = "noopener";
      where.append(link);
    } else {
      where.textContent = item.location;
    }
    const claims = item.cited_by.length
      ? (item.cited_by.length === 1 ? "Cited by claim " : "Cited by claims ") +
        item.cited_by.map(twoDigits).join(", ")
      : "Not cited by any claim";
    const view = html("div", "gw-item");
    view.append(
      back,
      html("p", "gw-eyebrow", words.join(" · ")),
      title(item.id),
      formatted(html("p", "gw-text stored"), item.text, item.runs),
      where,
      html("p", "gw-meta", claims),
      html("h3", "gw-sub", "Links (" + item.link_ids.length + ")")
    );
    const list = html("ul", "gw-list");
    for (const number of item.link_ids) {
      const link = state.graph.links[number];
      const direction =
        link.source === link.target ? "self" : link.source === item.id ? "out" : "in";
      const row = html("li");
      row.append(
        html("span", "gw-dir", direction),
        link.type + " ",
        idButton(direction === "in" ? link.source : link.target)
      );
      if (link.held) row.append(" HELD");
      const phrase = link.phrase === null ? "no phrase stored" : link.phrase;
      row.append(formatted(html("span", "gw-phrase stored"), phrase, link.phrase_runs));
      list.append(row);
    }
    if (item.link_ids.length === 0) view.append(html("p", "gw-meta", "No links."));
    else view.append(list);
    panel.replaceChildren(view);
    panel.scrollTop = 0;
  }

  // Zoom by `factor` about the canvas point (x, y), within the allowed range.
  function zoom(factor, x, y) {
    const scale = Math.min(
      state.fit.k * ZOOM_IN,
      Math.max(state.fit.k * ZOOM_OUT, state.view.k * factor)
    );
    const change = scale / state.view.k;
    state.view = {
      k: scale,
      x: x - (x - state.view.x) * change,
      y: y - (y - state.view.y) * change,
    };
    place();
  }

  function zoomAtCentre(factor) {
    const box = canvas.getBoundingClientRect();
    zoom(factor, box.width / 2, box.height / 2);
  }

  // The standard layout and the view of AC-25 again (AC-29, AC-29a); a later drag starts
  // a new live simulation from that layout.
  function reset() {
    stopLive();
    state.live = null;
    state.liveNodes = null;
    state.positions = standard(laid.get(state.slug).positions);
    state.fit = fitted();
    state.view = Object.assign({}, state.fit);
    state.size = canvas.getBoundingClientRect();
    place();
  }

  // Open the graph `slug`, or swap the open one for it; switch and selection start clear.
  function open(slug) {
    let found = laid.get(slug);
    if (!found) {
      const graph = JSON.parse(document.getElementById("graph-" + slug).textContent);
      found = { graph: graph, positions: layout(graph) };
      laid.set(slug, found);
    }
    stopLive();
    state = {
      slug: slug,
      graph: found.graph,
      positions: standard(found.positions),
      article: buttons.get(slug).closest("article"),
      selected: null,
    };
    heading.textContent = found.graph.label;
    counter.textContent = found.graph.position + " / " + found.graph.total;
    previousButton.disabled = found.graph.previous === null;
    nextButton.disabled = found.graph.next === null;
    const swapped = dialog.open;
    if (!swapped) dialog.showModal();
    state.fit = fitted();
    state.view = Object.assign({}, state.fit);
    state.size = canvas.getBoundingClientRect();
    draw();
    toggle.disabled = found.graph.cited_count === 0;
    filter(false);
    select(null);
    if (!swapped) closeButton.focus();
    // A focused previous or next button that is now disabled hands focus to the other.
    else if (document.activeElement === previousButton && previousButton.disabled) {
      nextButton.focus();
    } else if (document.activeElement === nextButton && nextButton.disabled) {
      previousButton.focus();
    }
  }

  // Under CLICK pixels of travel is a click that selects or clears. More, from a dot,
  // drags that dot and its neighbours follow; from empty canvas, it pans. Neither
  // selects (AC-27, AC-35).
  let drag = null;
  canvas.addEventListener("pointerdown", (event) => {
    if (!event.isPrimary || event.button !== 0) return;
    const item = nearest(event);
    drag = {
      pointer: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      item: item,
      from: Object.assign({}, state.view),
      at: item === null ? null : Object.assign({}, state.positions.get(item.id)),
      moving: false,
    };
  });
  // The dot a press would act on shows as hovered: its label and a pointer cursor.
  let hovered = null;
  function hover(item) {
    const node = item === null ? null : state.nodes.get(item.id);
    if (node === hovered) return;
    if (hovered) hovered.classList.remove("is-hover");
    if (node) node.classList.add("is-hover");
    hovered = node;
    canvas.classList.toggle("is-reach", node !== null);
  }
  canvas.addEventListener("pointerleave", () => {
    if (drag === null) hover(null);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (drag === null && event.pointerType !== "touch") hover(nearest(event));
    if (drag === null || event.pointerId !== drag.pointer) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moving) {
      if (Math.hypot(dx, dy) < CLICK) return;
      drag.moving = true;
      canvas.setPointerCapture(event.pointerId);
      canvas.classList.add("is-dragging");
      if (drag.item !== null) live().alphaTarget(WARM).restart();
    }
    if (drag.item === null) {
      state.view = { k: drag.from.k, x: drag.from.x + dx, y: drag.from.y + dy };
      place();
      return;
    }
    const node = state.liveNodes.get(drag.item.id);
    node.fx = drag.at.x + dx / state.view.k;
    node.fy = drag.at.y + dy / state.view.k;
  });
  function endDrag() {
    if (drag !== null && drag.moving && drag.item !== null) {
      const node = state.liveNodes.get(drag.item.id);
      node.fx = null;
      node.fy = null;
      // Let go, the graph settles; with reduced motion nothing moves on its own.
      if (STILL.matches) state.live.stop();
      else state.live.alphaTarget(0);
    }
    canvas.classList.remove("is-dragging");
  }
  canvas.addEventListener("pointerup", (event) => {
    if (drag === null || event.pointerId !== drag.pointer) return;
    const moved = drag.moving;
    const item = drag.item;
    endDrag();
    drag = null;
    if (!moved) select(item);
  });
  canvas.addEventListener("pointercancel", () => {
    endDrag();
    drag = null;
  });
  // Not passive, so neither the dialog scrolls nor a trackpad pinch zooms the page (AC-26).
  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const box = canvas.getBoundingClientRect();
      const lines = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? box.height : 1;
      const factor = Math.exp(-event.deltaY * lines * 0.002);
      zoom(factor, event.clientX - box.left, event.clientY - box.top);
    },
    { passive: false }
  );
  dialog.querySelector("[data-gw=zoom-in]").addEventListener("click", () => zoomAtCentre(STEP));
  dialog
    .querySelector("[data-gw=zoom-out]")
    .addEventListener("click", () => zoomAtCentre(1 / STEP));
  dialog.querySelector("[data-gw=reset]").addEventListener("click", reset);
  previousButton.addEventListener("click", () => open(state.graph.previous));
  nextButton.addEventListener("click", () => open(state.graph.next));

  // A cited id in a cloned claim, a link's other end, or a row of the item list: select
  // it, and keep a citation from leaving for JobHunt (AC-39, AC-51, AC-52).
  panel.addEventListener("click", (event) => {
    const link = event.target.closest("[data-item]");
    if (!link || !panel.contains(link)) return;
    event.preventDefault();
    const item = state.byId.get(link.dataset.item);
    if (item) choose(item);
  });
  toggle.addEventListener("change", () => filter(toggle.checked));
  // On a phone the key folds behind one button (AC-91).
  keyToggle.addEventListener("click", () => {
    const open = !foot.classList.contains("is-key-open");
    foot.classList.toggle("is-key-open", open);
    keyToggle.setAttribute("aria-expanded", String(open));
  });
  closeButton.addEventListener("click", () => dialog.close());
  // Esc, the close button and a back gesture all end here (AC-6).
  dialog.addEventListener("close", () => {
    stopLive();
    drag = null;
    const button = state && buttons.get(state.slug);
    if (button) button.focus();
  });
  // A resize keeps the reader's scale and the point at the canvas centre.
  window.addEventListener("resize", () => {
    if (!dialog.open || state === null) return;
    const box = canvas.getBoundingClientRect();
    state.view.x += (box.width - state.size.width) / 2;
    state.view.y += (box.height - state.size.height) / 2;
    state.size = box;
    state.fit = fitted();
    place();
  });

  for (const button of document.querySelectorAll("button[data-graph]")) {
    buttons.set(button.dataset.graph, button);
    button.addEventListener("click", () => open(button.dataset.graph));
    button.hidden = false;
  }
})();

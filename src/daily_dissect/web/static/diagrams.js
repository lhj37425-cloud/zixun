// 今日一拆 · 白板流程图
// Mermaid 提供图源码，Dagre 负责主路径布局；泳道、连线和卡片由本站绘制。

(function () {
  let lightbox = null;
  let boardEl = null;
  let lastFocus = null;
  let view = { x: 0, y: 0, scale: 1 };
  let drag = null;

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function cleanLabel(text) {
    return String(text || "")
      .trim()
      .replace(/^"|"$/g, "")
      .replace(/<br\s*\/?>/gi, "\n");
  }

  function laneRole(label) {
    if (/工具|文件|产物|输入/.test(label)) return "tools";
    if (/用户|使用者|读者/.test(label)) return "user";
    return "agent";
  }

  function parseFlow(source) {
    const nodes = new Map();
    const edges = [];
    const lanes = [];
    const laneMap = new Map();
    const coreIds = new Set();
    let direction = "LR";
    let currentLane = null;

    function ensureNode(id, label, kind, laneId) {
      const existing = nodes.get(id);
      if (!existing) {
        nodes.set(id, {
          id,
          label: cleanLabel(label || id),
          kind: kind || "rect",
          laneId: laneId || null,
        });
        return;
      }
      if (label && cleanLabel(label) !== id) existing.label = cleanLabel(label);
      if (kind && (kind === "diamond" || existing.kind !== "diamond")) existing.kind = kind;
      if (laneId && !existing.laneId) existing.laneId = laneId;
    }

    function takeNode(token, laneId) {
      const text = String(token || "").trim().replace(/;$/, "");
      if (!text) return null;
      const patterns = [
        { re: /^([A-Za-z][\w-]*)\[\s*"?([\s\S]*?)"?\s*\]$/, kind: "rect" },
        { re: /^([A-Za-z][\w-]*)\{\s*"?([\s\S]*?)"?\s*\}$/, kind: "diamond" },
        { re: /^([A-Za-z][\w-]*)\(\s*"?([\s\S]*?)"?\s*\)$/, kind: "stadium" },
        { re: /^([A-Za-z][\w-]*)$/, kind: "rect" },
      ];
      for (const pattern of patterns) {
        const match = text.match(pattern.re);
        if (!match) continue;
        ensureNode(match[1], match[2] || match[1], pattern.kind, laneId);
        return match[1];
      }
      return null;
    }

    source.split(/\r?\n/).forEach((raw) => {
      const line = raw.trim();
      if (!line || line.startsWith("%%")) return;

      const lane = line.match(/^subgraph\s+([A-Za-z][\w-]*)(?:\[\s*"?([^\]]*?)"?\s*\])?/i);
      if (lane) {
        const label = cleanLabel(lane[2] || lane[1]);
        currentLane = { id: lane[1], label, role: laneRole(label), nodeIds: [] };
        lanes.push(currentLane);
        laneMap.set(currentLane.id, currentLane);
        return;
      }
      if (/^end\s*;?$/i.test(line)) {
        currentLane = null;
        return;
      }

      const dir = line.match(/^flowchart\s+(TD|TB|LR|RL)\b/i);
      if (dir) {
        direction = dir[1].toUpperCase() === "TB" ? "TD" : dir[1].toUpperCase();
        return;
      }
      if (/^(flowchart|graph)\b/i.test(line)) return;

      const coreLine = line.match(/^class\s+([\w,-]+)\s+([\w-]+)\s*$/i);
      if (coreLine) {
        if (coreLine[2].toLowerCase() === "core") {
          coreLine[1].split(",").forEach((id) => coreIds.add(id.trim()));
        }
        return;
      }

      const laneId = currentLane && currentLane.id;
      const parts = line.split(/\s*(-\.->|-->)\s*/);
      if (parts.length < 3) {
        takeNode(line, laneId);
        return;
      }
      let fromToken = parts[0];
      for (let index = 1; index < parts.length; index += 2) {
        let toToken = parts[index + 1] || "";
        let label = "";
        const labeledTarget = toToken.match(/^\|([^|]*)\|\s*(.*)$/);
        if (labeledTarget) {
          label = labeledTarget[1];
          toToken = labeledTarget[2];
        }
        const from = takeNode(fromToken, laneId);
        const to = takeNode(toToken, laneId);
        if (from && to) {
          edges.push({ from, to, label: cleanLabel(label), dotted: parts[index] === "-.->" });
        }
        fromToken = toToken;
      }
    });

    nodes.forEach((node) => {
      const lane = node.laneId && laneMap.get(node.laneId);
      node.role = lane ? lane.role : "agent";
      node.core = coreIds.has(node.id);
      if (lane) lane.nodeIds.push(node.id);
    });

    return { direction, nodes: [...nodes.values()], edges, lanes };
  }

  function displayWidth(text) {
    return [...String(text)].reduce((width, char) => width + (char.charCodeAt(0) > 255 ? 2 : 1), 0);
  }

  function wrapLabel(node) {
    const maxUnits = node.role === "tools" ? 18 : node.kind === "diamond" ? 14 : 20;
    const lines = [];
    node.label.split("\n").forEach((part) => {
      let line = "";
      let width = 0;
      [...part].forEach((char) => {
        const charWidth = char.charCodeAt(0) > 255 ? 2 : 1;
        if (line && width + charWidth > maxUnits) {
          lines.push(line);
          line = "";
          width = 0;
        }
        line += char;
        width += charWidth;
      });
      lines.push(line || " ");
    });
    node.lines = lines.slice(0, 4);
    if (node.kind === "diamond") {
      node.width = 208;
      node.height = 118;
      return;
    }
    node.width = node.role === "tools" ? 168 : 190;
    node.height = Math.max(76, 34 + node.lines.length * 22);
  }

  function isSupportEdge(edge, nodeMap) {
    const target = nodeMap.get(edge.to);
    const source = nodeMap.get(edge.from);
    return edge.dotted || Boolean(target && source && target.role === "tools" && source.role !== "tools");
  }

  function findBackEdges(parsed, nodeMap) {
    const outgoing = new Map(parsed.nodes.map((node) => [node.id, []]));
    parsed.edges.forEach((edge) => {
      if (!isSupportEdge(edge, nodeMap) && outgoing.has(edge.from)) outgoing.get(edge.from).push(edge);
    });
    const state = new Map();
    const back = new Set();

    function visit(id) {
      state.set(id, 1);
      (outgoing.get(id) || []).forEach((edge) => {
        if (state.get(edge.to) === 1) back.add(edge);
        else if (!state.get(edge.to)) visit(edge.to);
      });
      state.set(id, 2);
    }

    parsed.nodes.forEach((node) => {
      if (!state.get(node.id)) visit(node.id);
    });
    return back;
  }

  function layoutBoard(parsed) {
    if (!window.dagre) throw new Error("Dagre 未加载");
    const nodeMap = new Map(parsed.nodes.map((node) => [node.id, node]));
    parsed.nodes.forEach(wrapLabel);
    const backEdges = findBackEdges(parsed, nodeMap);
    const hasLanes = parsed.lanes.some((lane) => lane.nodeIds.length);
    const mainNodes = parsed.nodes.filter((node) => !hasLanes || node.role !== "tools");
    const rankdir = hasLanes ? "LR" : parsed.direction === "TD" ? "TB" : "LR";
    const graph = new window.dagre.graphlib.Graph().setGraph({
      rankdir,
      ranksep: 56,
      nodesep: 44,
      edgesep: 24,
      marginx: 40,
      marginy: 44,
    });
    graph.setDefaultEdgeLabel(() => ({}));
    mainNodes.forEach((node) => graph.setNode(node.id, { width: node.width, height: node.height }));
    parsed.edges.forEach((edge) => {
      if (backEdges.has(edge) || isSupportEdge(edge, nodeMap)) return;
      if (graph.hasNode(edge.from) && graph.hasNode(edge.to)) graph.setEdge(edge.from, edge.to);
    });
    window.dagre.layout(graph);

    const positions = new Map();
    mainNodes.forEach((node) => {
      const point = graph.node(node.id);
      positions.set(node.id, {
        x: point.x - node.width / 2,
        y: point.y - node.height / 2,
        w: node.width,
        h: node.height,
      });
    });

    const graphSize = graph.graph();
    let lanes = [];
    let baseHeight = graphSize.height + 96;
    let canvasWidth = Math.max(920, graphSize.width + 64);

    if (hasLanes) {
      lanes = parsed.lanes.filter((lane) => lane.nodeIds.length);
      const ungrouped = mainNodes.filter((node) => !node.laneId).map((node) => node.id);
      if (ungrouped.length) lanes.unshift({ id: "__flow", label: "流程", role: "agent", nodeIds: ungrouped });
      let y = 20;
      lanes.forEach((lane) => {
        lane.height = lane.role === "tools" ? 172 : 176;
        lane.y = y;
        y += lane.height + 18;
        lane.nodeIds.forEach((id) => {
          const node = nodeMap.get(id);
          const position = positions.get(id);
          if (!node || !position || node.role === "tools") return;
          position.y = lane.y + (lane.height - position.h) / 2;
        });
      });
      baseHeight = y + 8;

      const toolsLane = lanes.find((lane) => lane.role === "tools");
      const toolSources = new Map();
      parsed.edges.forEach((edge) => {
        const target = nodeMap.get(edge.to);
        if (!target || target.role !== "tools" || !positions.has(edge.from)) return;
        if (!toolSources.has(edge.to)) toolSources.set(edge.to, edge.from);
      });
      const sourceGroups = new Map();
      toolSources.forEach((source, target) => {
        if (!sourceGroups.has(source)) sourceGroups.set(source, []);
        sourceGroups.get(source).push(target);
      });
      sourceGroups.forEach((targets, source) => {
        const sourcePosition = positions.get(source);
        targets.forEach((id, index) => {
          const node = nodeMap.get(id);
          const offset = (index - (targets.length - 1) / 2) * (node.width + 20);
          positions.set(id, {
            x: sourcePosition.x + sourcePosition.w / 2 - node.width / 2 + offset,
            y: toolsLane.y + (toolsLane.height - node.height) / 2,
            w: node.width,
            h: node.height,
          });
        });
      });
      parsed.nodes.filter((node) => node.role === "tools" && !positions.has(node.id)).forEach((node, index) => {
        positions.set(node.id, {
          x: 32 + index * (node.width + 24),
          y: toolsLane ? toolsLane.y + (toolsLane.height - node.height) / 2 : 64,
          w: node.width,
          h: node.height,
        });
      });
    }

    positions.forEach((position) => {
      canvasWidth = Math.max(canvasWidth, position.x + position.w + 96);
      baseHeight = Math.max(baseHeight, position.y + position.h + 64);
    });
    canvasWidth = Math.max(canvasWidth, 920);
    const feedbackHeight = backEdges.size ? backEdges.size * 34 + 56 : 0;
    const canvasHeight = baseHeight + feedbackHeight;
    lanes.forEach((lane) => {
      lane.x = 28;
      lane.width = canvasWidth - 44;
    });

    return { positions, lanes, backEdges, nodeMap, width: canvasWidth, height: canvasHeight, baseHeight };
  }

  function centers(position) {
    return {
      cx: position.x + position.w / 2,
      cy: position.y + position.h / 2,
      left: position.x,
      right: position.x + position.w,
      top: position.y,
      bottom: position.y + position.h,
    };
  }

  function edgeLabel(x, y, label, kind, align) {
    if (!label) return "";
    const width = Math.min(180, Math.max(36, displayWidth(label) * 7 + 12));
    const left = align === "left" ? x : x - width / 2;
    return (
      `<foreignObject x="${left}" y="${y - 13}" width="${width}" height="26">` +
      `<div xmlns="http://www.w3.org/1999/xhtml" class="board-edge-label ${kind || ""}">${escapeHtml(label)}</div>` +
      `</foreignObject>`
    );
  }

  function backPath(a, b, channelY, laid, targetId) {
    const lane = laid.lanes.find((item) => item.nodeIds.includes(targetId));
    if (!lane) return `M ${a.cx} ${a.bottom} V ${channelY} H 12 V ${b.cy} H ${b.left}`;
    const gapY = lane.y + lane.height + 9;
    return `M ${a.cx} ${a.bottom} V ${channelY} H 12 V ${gapY} H ${b.cx} V ${b.bottom}`;
  }

  function renderEdges(parsed, laid) {
    let backIndex = 0;
    return parsed.edges.map((edge) => {
      const from = laid.positions.get(edge.from);
      const to = laid.positions.get(edge.to);
      if (!from || !to) return "";
      const a = centers(from);
      const b = centers(to);
      const isBack = laid.backEdges.has(edge);
      const isSupport = isSupportEdge(edge, laid.nodeMap);

      // 回边（修改、重试、下一轮）：从下方绕出去，沿画布左侧上来，从泳道空隙进目标底部
      if (isBack) {
        const channelY = laid.baseHeight + 30 + backIndex * 34;
        backIndex += 1;
        const d = backPath(a, b, channelY, laid, edge.to);
        return `<path class="board-edge is-back" d="${d}" />` +
          edgeLabel((a.cx + 12) / 2, channelY - 16, edge.label, "is-back");
      }

      // 工具与产物：竖直虚线
      if (isSupport) {
        const down = b.cy >= a.cy;
        const startY = down ? a.bottom : a.top;
        const endY = down ? b.top : b.bottom;
        return `<path class="board-edge is-support" d="M ${a.cx} ${startY} V ${endY}" />` +
          edgeLabel(a.cx + 8, (startY + endY) / 2, edge.label, "is-support", "left");
      }

      // 目标在左边又不是回边：按回边的方式绕，避免横穿卡片
      if (b.left < a.right - 1) {
        const channelY = laid.baseHeight + 30 + backIndex * 34;
        backIndex += 1;
        const d = backPath(a, b, channelY, laid, edge.to);
        return `<path class="board-edge" d="${d}" />` +
          edgeLabel((a.cx + 12) / 2, channelY - 16, edge.label, "");
      }

      if (Math.abs(a.cy - b.cy) < 1.5) {
        return `<path class="board-edge" d="M ${a.right} ${a.cy} H ${b.left}" />` +
          edgeLabel((a.right + b.left) / 2, a.cy - 17, edge.label, "");
      }

      const midX = (a.right + b.left) / 2;
      const d = `M ${a.right} ${a.cy} H ${midX} V ${b.cy} H ${b.left}`;
      return `<path class="board-edge" d="${d}" />` +
        edgeLabel(midX, (a.cy + b.cy) / 2, edge.label, "is-jog");
    }).join("");
  }

  function renderBoard(source) {
    const parsed = parseFlow(source);
    if (!parsed.nodes.length) return '<p class="board-empty">这张流程图还没有可展示的步骤。</p>';
    const laid = layoutBoard(parsed);
    const laneHtml = laid.lanes.map((lane) => (
      `<section class="board-lane is-${lane.role}" style="left:${lane.x}px;top:${lane.y}px;width:${lane.width}px;height:${lane.height}px">` +
      `<p class="board-lane-label">${escapeHtml(lane.label)}</p>` +
      `</section>`
    )).join("");

    const nodeHtml = parsed.nodes.map((node) => {
      const p = laid.positions.get(node.id);
      if (!p) return "";
      const text = node.lines.map((line) => `<span>${escapeHtml(line)}</span>`).join("");
      const classes = ["board-card", `is-${node.role}`, `is-${node.kind}`];
      if (node.core) classes.push("is-core");
      const style = `left:${p.x}px;top:${p.y}px;width:${p.w}px;height:${p.h}px`;
      if (node.kind === "diamond") {
        const shape = `<svg class="board-diamond" viewBox="0 0 ${p.w} ${p.h}" preserveAspectRatio="none" aria-hidden="true">` +
          `<polygon points="${p.w / 2},1 ${p.w - 1},${p.h / 2} ${p.w / 2},${p.h - 1} 1,${p.h / 2}"></polygon></svg>`;
        return `<article class="${classes.join(" ")}" style="${style}">${shape}<span class="board-card-text">${text}</span></article>`;
      }
      return `<article class="${classes.join(" ")}" style="${style}"><span class="board-card-text">${text}</span></article>`;
    }).join("");

    return (
      `<div class="board-canvas" style="width:${laid.width}px;height:${laid.height}px">` +
      laneHtml +
      `<svg class="board-edges" width="${laid.width}" height="${laid.height}" aria-hidden="true">` +
      `<defs>` +
      `<marker id="board-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="board-arrow-main" d="M 0 0 L 10 5 L 0 10 z"></path></marker>` +
      `<marker id="board-arrow-back" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="board-arrow-back" d="M 0 0 L 10 5 L 0 10 z"></path></marker>` +
      `<marker id="board-arrow-support" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path class="board-arrow-support" d="M 0 0 L 10 5 L 0 10 z"></path></marker>` +
      `</defs>${renderEdges(parsed, laid)}</svg>` +
      nodeHtml +
      `<div class="board-legend"><span><i class="is-main"></i>主流程</span><span><i class="is-back"></i>返工 / 循环</span><span><i class="is-support"></i>输入与产物</span></div>` +
      `</div>`
    );
  }

  function applyView() {
    if (!boardEl) return;
    boardEl.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
    const label = lightbox && lightbox.querySelector("[data-diagram-zoom-label]");
    if (label) label.textContent = `${Math.round(view.scale * 100)}%`;
  }

  function fitToView() {
    const body = lightbox && lightbox.querySelector(".diagram-lightbox-body");
    const canvas = boardEl && boardEl.querySelector(".board-canvas");
    if (!body || !canvas) return;
    const pad = 48;
    const maxW = Math.max(160, body.clientWidth - pad);
    const maxH = Math.max(160, body.clientHeight - pad);
    const width = canvas.offsetWidth || 800;
    const height = canvas.offsetHeight || 600;
    const scale = Math.min(maxW / width, maxH / height, 1.05);
    view.scale = Math.max(0.25, scale);
    view.x = (body.clientWidth - width * view.scale) / 2;
    view.y = (body.clientHeight - height * view.scale) / 2;
    applyView();
  }

  function zoomBy(factor, cx, cy) {
    const body = lightbox && lightbox.querySelector(".diagram-lightbox-body");
    if (!body) return;
    const rect = body.getBoundingClientRect();
    const pivotX = cx == null ? rect.width / 2 : cx - rect.left;
    const pivotY = cy == null ? rect.height / 2 : cy - rect.top;
    const next = Math.min(2.4, Math.max(0.25, view.scale * factor));
    const ratio = next / view.scale;
    view.x = pivotX - (pivotX - view.x) * ratio;
    view.y = pivotY - (pivotY - view.y) * ratio;
    view.scale = next;
    applyView();
  }

  function ensureLightbox() {
    if (lightbox) return;
    lightbox = document.createElement("div");
    lightbox.className = "diagram-lightbox";
    lightbox.hidden = true;
    lightbox.innerHTML = `
      <div class="diagram-lightbox-backdrop" data-diagram-close tabindex="-1"></div>
      <div class="diagram-lightbox-panel" role="dialog" aria-modal="true" aria-label="流程图">
        <div class="diagram-lightbox-bar">
          <p class="diagram-lightbox-title">流程图</p>
          <div class="diagram-lightbox-tools">
            <button type="button" class="btn btn-ghost" data-diagram-zoom-out aria-label="缩小">−</button>
            <span class="diagram-zoom-label" data-diagram-zoom-label>100%</span>
            <button type="button" class="btn btn-ghost" data-diagram-zoom-in aria-label="放大">+</button>
            <button type="button" class="btn btn-ghost" data-diagram-fit>适应窗口</button>
            <button type="button" class="btn btn-ghost diagram-lightbox-close" data-diagram-close>关闭</button>
          </div>
        </div>
        <div class="diagram-lightbox-body">
          <div class="diagram-lightbox-host"><div class="diagram-stage board-stage"></div></div>
        </div>
      </div>
    `;
    document.body.appendChild(lightbox);
    boardEl = lightbox.querySelector(".board-stage");

    lightbox.addEventListener("click", (event) => {
      if (event.target.closest("[data-diagram-close]")) closeLightbox();
      else if (event.target.closest("[data-diagram-zoom-in]")) zoomBy(1.12);
      else if (event.target.closest("[data-diagram-zoom-out]")) zoomBy(1 / 1.12);
      else if (event.target.closest("[data-diagram-fit]")) fitToView();
    });

    const body = lightbox.querySelector(".diagram-lightbox-body");
    body.addEventListener("wheel", (event) => {
      if (lightbox.hidden) return;
      event.preventDefault();
      zoomBy(event.deltaY < 0 ? 1.08 : 1 / 1.08, event.clientX, event.clientY);
    }, { passive: false });
    body.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, ox: view.x, oy: view.y };
      body.setPointerCapture(event.pointerId);
      body.classList.add("is-dragging");
    });
    body.addEventListener("pointermove", (event) => {
      if (!drag || drag.id !== event.pointerId) return;
      view.x = drag.ox + (event.clientX - drag.x);
      view.y = drag.oy + (event.clientY - drag.y);
      applyView();
    });
    function endDrag(event) {
      if (!drag || drag.id !== event.pointerId) return;
      drag = null;
      body.classList.remove("is-dragging");
    }
    body.addEventListener("pointerup", endDrag);
    body.addEventListener("pointercancel", endDrag);
  }

  function openLightbox(source, title) {
    ensureLightbox();
    lastFocus = document.activeElement;
    const titleEl = lightbox.querySelector(".diagram-lightbox-title");
    if (titleEl) titleEl.textContent = title || "流程图";
    try {
      boardEl.innerHTML = renderBoard(source);
    } catch (error) {
      boardEl.innerHTML = `<p class="board-empty">流程图暂时无法显示：${escapeHtml(error.message)}</p>`;
    }
    view = { x: 0, y: 0, scale: 1 };
    lightbox.hidden = false;
    document.body.classList.add("has-diagram-lightbox");
    lightbox.querySelector("[data-diagram-close].diagram-lightbox-close")?.focus();
    requestAnimationFrame(() => requestAnimationFrame(fitToView));
  }

  function closeLightbox() {
    if (!lightbox || lightbox.hidden) return;
    lightbox.hidden = true;
    document.body.classList.remove("has-diagram-lightbox");
    if (boardEl) boardEl.innerHTML = "";
    drag = null;
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-diagram-open]");
    if (!button) return;
    const launch = button.closest(".diagram-launch");
    const sourceEl = launch && launch.querySelector(".diagram-source");
    if (!sourceEl) return;
    const heading = launch.parentElement?.querySelector("h3, h4");
    openLightbox(sourceEl.textContent, heading ? heading.textContent.trim() : "流程图");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeLightbox();
  });

  window.addEventListener("resize", () => {
    if (lightbox && !lightbox.hidden) fitToView();
  });
})();

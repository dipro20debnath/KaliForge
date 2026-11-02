"""A lightweight layered-tree graph view for the Attack Surface Mapper, built on
QGraphicsView (no external graph libraries). Lays nodes out left-to-right by
level and draws edges as curves."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsPathItem,
                               QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView)

from core.attack_surface import Graph

KIND_COLORS = {
    "domain": "#27e0a1", "subdomain": "#13c2c2", "host": "#4dabf7",
    "ip": "#3fa9ff", "url": "#c38cff", "port": "#ffd23f", "service": "#ff8c1a",
}
_NODE_W = 150
_NODE_H = 30
_X_GAP = 90
_Y_GAP = 12


class GraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QColor("#05080a"))
        self._scale = 1.0

    def wheelEvent(self, event):  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_scale = self._scale * factor
        if 0.3 <= new_scale <= 3.0:
            self._scale = new_scale
            self.scale(factor, factor)

    def set_graph(self, graph: Graph) -> None:
        scene = self.scene()
        scene.clear()
        if not graph.nodes:
            text = scene.addText("No assets yet — seed from scope / findings, "
                                 "or import tool output.", QFont("Inter", 11))
            text.setDefaultTextColor(QColor("#7f9499"))
            return

        # assign levels via BFS from roots
        by_id = {n.id: n for n in graph.nodes}
        children: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
        for parent, child in graph.edges:
            if parent in children:
                children[parent].append(child)
        level: dict[str, int] = {}
        order: list[str] = []
        queue = [(r.id, 0) for r in graph.roots()]
        visited = set()
        while queue:
            nid, lvl = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            level[nid] = lvl
            order.append(nid)
            for child in children.get(nid, []):
                queue.append((child, lvl + 1))
        # any disconnected nodes
        for n in graph.nodes:
            if n.id not in level:
                level[n.id] = 0
                order.append(n.id)

        # group by level, assign y per column
        columns: dict[int, list[str]] = {}
        for nid in order:
            columns.setdefault(level[nid], []).append(nid)

        positions: dict[str, QPointF] = {}
        for lvl, ids in sorted(columns.items()):
            x = lvl * (_NODE_W + _X_GAP)
            total_h = len(ids) * (_NODE_H + _Y_GAP)
            y0 = -total_h / 2
            for i, nid in enumerate(ids):
                y = y0 + i * (_NODE_H + _Y_GAP)
                positions[nid] = QPointF(x, y)

        # edges first (under nodes)
        edge_pen = QPen(QColor("#1f2e32"), 1.4)
        for parent, child in graph.edges:
            if parent in positions and child in positions:
                p1 = positions[parent] + QPointF(_NODE_W, _NODE_H / 2)
                p2 = positions[child] + QPointF(0, _NODE_H / 2)
                path = QPainterPath(p1)
                midx = (p1.x() + p2.x()) / 2
                path.cubicTo(QPointF(midx, p1.y()), QPointF(midx, p2.y()), p2)
                item = QGraphicsPathItem(path)
                item.setPen(edge_pen)
                scene.addItem(item)

        # nodes
        for nid, pos in positions.items():
            node = by_id[nid]
            color = QColor(KIND_COLORS.get(node.kind, "#7f9499"))
            rect = scene.addRect(QRectF(pos.x(), pos.y(), _NODE_W, _NODE_H),
                                 QPen(color, 1.6), QBrush(QColor("#11181a")))
            rect.setToolTip(f"{node.kind}: {node.label}")
            # kind dot
            dot = QGraphicsEllipseItem(pos.x() + 8, pos.y() + _NODE_H / 2 - 4, 8, 8, rect)
            dot.setBrush(QBrush(color))
            dot.setPen(QPen(Qt.NoPen))
            label = node.label if len(node.label) <= 18 else node.label[:17] + "…"
            text = QGraphicsSimpleTextItem(label, rect)
            text.setBrush(QBrush(QColor("#d6e4e6")))
            text.setFont(QFont("Inter", 9))
            text.setPos(pos.x() + 22, pos.y() + 8)

        self.setSceneRect(scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))

    def fit(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-30, -30, 30, 30), Qt.KeepAspectRatio)
            self._scale = 1.0

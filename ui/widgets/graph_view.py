"""A lightweight layered-tree graph view for the Attack Surface Mapper, built on
QGraphicsView (no external graph libraries). Nodes are draggable with live edge
updates, the view zooms/pans, and the scene can be exported to PNG."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QPainter, QPainterPath,
                           QPen)
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                               QGraphicsPathItem, QGraphicsRectItem,
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

# themeable colours (updated via GraphView.set_theme)
THEME = {"bg": "#05080a", "node_bg": "#11181a", "text": "#d6e4e6", "edge": "#2b4047"}


class EdgeItem(QGraphicsPathItem):
    def __init__(self, src: "NodeItem", dst: "NodeItem"):
        super().__init__()
        self.src = src
        self.dst = dst
        self.setPen(QPen(QColor(THEME["edge"]), 1.4))
        self.setZValue(-1)
        self.update_path()

    def update_path(self) -> None:
        p1 = self.src.scenePos() + QPointF(_NODE_W, _NODE_H / 2)
        p2 = self.dst.scenePos() + QPointF(0, _NODE_H / 2)
        path = QPainterPath(p1)
        midx = (p1.x() + p2.x()) / 2
        path.cubicTo(QPointF(midx, p1.y()), QPointF(midx, p2.y()), p2)
        self.setPath(path)


class NodeItem(QGraphicsRectItem):
    def __init__(self, label: str, kind: str):
        super().__init__(0, 0, _NODE_W, _NODE_H)
        color = QColor(KIND_COLORS.get(kind, "#7f9499"))
        self.setPen(QPen(color, 1.6))
        self.setBrush(QBrush(QColor(THEME["node_bg"])))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setToolTip(f"{kind}: {label}")
        self.edges: list[EdgeItem] = []

        dot = QGraphicsEllipseItem(8, _NODE_H / 2 - 4, 8, 8, self)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.NoPen))
        shown = label if len(label) <= 18 else label[:17] + "…"
        text = QGraphicsSimpleTextItem(shown, self)
        text.setBrush(QBrush(QColor(THEME["text"])))
        text.setFont(QFont("Inter", 9))
        text.setPos(22, 8)

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_path()
        return super().itemChange(change, value)


class GraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setBackgroundBrush(QColor(THEME["bg"]))
        self._scale = 1.0

    def set_theme(self, bg: str, node_bg: str, text: str, edge: str) -> None:
        THEME.update({"bg": bg, "node_bg": node_bg, "text": text, "edge": edge})
        self.setBackgroundBrush(QColor(bg))

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
            self.setSceneRect(QRectF(-200, -100, 400, 200))
            return

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
        for n in graph.nodes:
            if n.id not in level:
                level[n.id] = 0
                order.append(n.id)

        columns: dict[int, list[str]] = {}
        for nid in order:
            columns.setdefault(level[nid], []).append(nid)

        items: dict[str, NodeItem] = {}
        for lvl, ids in sorted(columns.items()):
            x = lvl * (_NODE_W + _X_GAP)
            total_h = len(ids) * (_NODE_H + _Y_GAP)
            y0 = -total_h / 2
            for i, nid in enumerate(ids):
                node = by_id[nid]
                item = NodeItem(node.label, node.kind)
                item.setPos(x, y0 + i * (_NODE_H + _Y_GAP))
                scene.addItem(item)
                items[nid] = item

        for parent, child in graph.edges:
            if parent in items and child in items:
                edge = EdgeItem(items[parent], items[child])
                scene.addItem(edge)
                items[parent].edges.append(edge)
                items[child].edges.append(edge)

        self.setSceneRect(scene.itemsBoundingRect().adjusted(-60, -60, 60, 60))

    def fit(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-30, -30, 30, 30), Qt.KeepAspectRatio)
            self._scale = 1.0

    def export_png(self, path: str) -> bool:
        scene = self.scene()
        rect = scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        if rect.isEmpty():
            return False
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(QColor(THEME["bg"]))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        scene.render(painter, target=QRectF(image.rect()), source=rect)
        painter.end()
        return image.save(path)

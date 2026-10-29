"use client";

import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

type Position = { x: number; y: number };

const STORAGE_KEY = "hrms-assistant-position";

function clampPosition(position: Position, width: number, height: number): Position {
  return {
    x: Math.min(Math.max(8, position.x), Math.max(8, window.innerWidth - width - 8)),
    y: Math.min(Math.max(8, position.y), Math.max(8, window.innerHeight - height - 8)),
  };
}

/** A floating assistant that can be repositioned by dragging its header. */
export function DraggableAssistant({ children }: { children: ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ pointerId: number; offsetX: number; offsetY: number } | null>(null);
  const [position, setPosition] = useState<Position | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Position | null;
      if (saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
        const element = containerRef.current;
        if (element) {
          setPosition(clampPosition(saved, element.offsetWidth, element.offsetHeight));
        }
      }
    } catch {
      // A stale or blocked local-storage value should not affect the assistant.
    }
  }, []);

  useEffect(() => {
    function stopDragging() {
      if (!dragRef.current) return;
      dragRef.current = null;
      setDragging(false);
      if (position) {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(position));
        } catch {
          // Persistence is optional; dragging still works without it.
        }
      }
    }

    function move(event: PointerEvent) {
      const drag = dragRef.current;
      const element = containerRef.current;
      if (!drag || !element || event.pointerId !== drag.pointerId) return;
      const next = clampPosition(
        { x: event.clientX - drag.offsetX, y: event.clientY - drag.offsetY },
        element.offsetWidth,
        element.offsetHeight,
      );
      setPosition(next);
    }

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);
    window.addEventListener("resize", stopDragging);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stopDragging);
      window.removeEventListener("pointercancel", stopDragging);
      window.removeEventListener("resize", stopDragging);
    };
  }, [position]);

  function startDragging(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    const target = event.target;
    if (!(target instanceof Element) || !target.closest(".assistant-head")) return;
    const element = containerRef.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    setPosition({ x: rect.left, y: rect.top });
    setDragging(true);
    event.preventDefault();
  }

  return (
    <div
      ref={containerRef}
      className={`draggable-assistant${dragging ? " is-dragging" : ""}`}
      onPointerDown={startDragging}
      aria-label="Floating HRMS assistant; drag the header to reposition"
    >
      {children}
    </div>
  );
}

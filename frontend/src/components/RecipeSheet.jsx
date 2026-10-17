import { useId, useLayoutEffect, useRef, useState } from "react";
import { animate, motion as Motion, useMotionValue, useReducedMotion } from "framer-motion";
import { useLocale } from "../context/LocaleContext";

export default function RecipeSheet({ children, inline = false }) {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const gesture = useRef(null);
  const dragged = useRef(false);
  const lastScrollTop = useRef(0);
  const touchY = useRef(null);
  const contentId = useId();
  const sheetRef = useRef(null);
  const sheetTop = useMotionValue("45%");
  const shouldReduceMotion = useReducedMotion();

  useLayoutEffect(() => {
    if (inline) return;
    const parent = sheetRef.current.parentElement;
    let height = parent.clientHeight;
    const target = expanded ? Math.min(128, height * 0.2) : height * 0.45;
    let animation;
    if (shouldReduceMotion || typeof sheetTop.get() !== "number") sheetTop.set(target);
    else animation = animate(sheetTop, target, { type: "spring", stiffness: 300, damping: 30 });

    const observer = new ResizeObserver(() => {
      if (height === parent.clientHeight) return;
      height = parent.clientHeight;
      animation?.stop();
      sheetTop.set(expanded ? Math.min(128, height * 0.2) : height * 0.45);
    });
    observer.observe(parent);
    return () => { animation?.stop(); observer.disconnect(); };
  }, [expanded, inline, sheetTop, shouldReduceMotion]);

  const startDrag = (event) => {
    if (event.button !== 0) return;
    gesture.current = { id: event.pointerId, y: event.clientY };
    dragged.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const endDrag = (event) => {
    if (gesture.current?.id !== event.pointerId) return;
    const distance = event.clientY - gesture.current.y;
    gesture.current = null;
    if (Math.abs(distance) >= 24) {
      dragged.current = true;
      setExpanded(distance < 0);
    }
  };

  const toggleSheet = (event) => {
    const wasDragged = dragged.current;
    dragged.current = false;
    if (!wasDragged || event.detail === 0) setExpanded(value => !value);
  };

  const resizeAtEdge = (element, direction) => {
    if (inline) return;
    const remaining = element.scrollHeight - element.clientHeight;
    if (direction > 0 && remaining > 1 && remaining - element.scrollTop <= 1) setExpanded(true);
    else if (direction < 0 && element.scrollTop <= 1) setExpanded(false);
  };

  const handleScroll = (event) => {
    const element = event.currentTarget;
    const direction = element.scrollTop - lastScrollTop.current;
    lastScrollTop.current = element.scrollTop;
    // A larger sheet can clamp scrollTop to zero; that resize is not an upward gesture.
    if (element.scrollHeight - element.clientHeight > 1) resizeAtEdge(element, direction);
  };

  const handleWheel = (event) => resizeAtEdge(event.currentTarget, event.deltaY);
  const handleTouchStart = (event) => {
    touchY.current = event.touches.length === 1 ? event.touches[0].clientY : null;
  };
  const handleTouchMove = (event) => {
    if (event.touches.length !== 1) { touchY.current = null; return; }
    if (touchY.current === null) return;
    const nextY = event.touches[0].clientY;
    resizeAtEdge(event.currentTarget, touchY.current - nextY);
    touchY.current = nextY;
  };

  return (
    <Motion.section ref={sheetRef} style={inline ? undefined : { top: sheetTop }} className={`recipe-sheet${inline ? " recipe-sheet--inline" : ""}`} data-expanded={expanded} aria-label={t("รายละเอียดสูตรอาหาร")}>
      {!inline && (
        <button type="button" className="recipe-sheet-handle" aria-expanded={expanded} aria-controls={contentId}
          aria-label={t(expanded ? "ย่อการ์ดสูตรอาหาร" : "ขยายการ์ดสูตรอาหาร")}
          onPointerDown={startDrag} onPointerUp={endDrag}
          onPointerCancel={() => { gesture.current = null; dragged.current = false; }}
          onLostPointerCapture={() => { gesture.current = null; }}
          onClick={toggleSheet}>
          <span aria-hidden="true" />
        </button>
      )}
      <div id={contentId} className="recipe-sheet-scroll recipe-reading scrollbar-hide" tabIndex={0} aria-label={t("เนื้อหาสูตรอาหาร")} role="region"
        onScroll={handleScroll} onWheel={handleWheel} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove}
        onTouchEnd={() => { touchY.current = null; }} onTouchCancel={() => { touchY.current = null; }}>
        {children}
      </div>
    </Motion.section>
  );
}

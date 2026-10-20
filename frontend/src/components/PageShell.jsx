import { useLayoutEffect, useRef } from "react";

export default function PageShell({ children, className = "", frameClassName = "", contained = false, lockScroll = false, scrollKey, initialScroll = 0 }) {
  const frame = useRef(null);

  useLayoutEffect(() => {
    window.scrollTo({ top: initialScroll, behavior: "instant" });
  }, [scrollKey, initialScroll]);

  useLayoutEffect(() => {
    const element = frame.current;
    const nav = element.querySelector("nav");
    const actions = element.querySelector(":scope > .page-actions");
    const measure = () => {
      const navHeight = nav?.getBoundingClientRect().height ?? 0;
      const actionsHeight = actions?.getBoundingClientRect().height ?? 0;
      element.style.setProperty("--bottom-menu-height", `${navHeight}px`);
      element.style.setProperty("--page-bottom-clearance", `${navHeight + actionsHeight}px`);
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (nav) observer.observe(nav);
    if (actions) observer.observe(actions);
    return () => observer.disconnect();
  }, [scrollKey, contained]);

  useLayoutEffect(() => {
    if (!contained && !lockScroll) return;
    const top = window.scrollY;
    const body = document.body;
    const previous = { position: body.style.position, top: body.style.top, width: body.style.width, overflow: body.style.overflow };
    const overscroll = document.documentElement.style.overscrollBehaviorY;
    // Fixed body also prevents Safari from scrolling the background behind a sheet.
    Object.assign(body.style, { position: "fixed", top: `-${top}px`, width: "100%", overflow: "hidden" });
    document.documentElement.style.overscrollBehaviorY = "none";
    return () => {
      Object.assign(body.style, previous);
      document.documentElement.style.overscrollBehaviorY = overscroll;
      window.scrollTo({ top, behavior: "instant" });
    };
  }, [contained, lockScroll]);

  return <div className={`${className} ${contained ? "h-dvh overflow-hidden" : "min-h-dvh"} bg-gray-100 flex justify-center font-sans`}>
    <div ref={frame} className={`page-frame${contained ? " page-frame--contained" : ""} w-full max-w-107.5 bg-white relative flex flex-col shadow-2xl ${frameClassName}`}>
      {children}
    </div>
  </div>;
}

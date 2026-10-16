import { useRef } from "react";

export default function DragScrollRow({ children, className = "", ...props }) {
    const drag = useRef({ isDown: false, startX: 0, scrollLeft: 0, moved: false });

    const handleMouseDown = (event) => {
        if (event.button !== 0) return;
        const row = event.currentTarget;
        drag.current = { isDown: true, startX: event.pageX - row.offsetLeft, scrollLeft: row.scrollLeft, moved: false };
    };
    const handleMouseMove = (event) => {
        if (!drag.current.isDown) return;
        if (!(event.buttons & 1)) {
            drag.current.isDown = false;
            return;
        }
        event.preventDefault();
        const row = event.currentTarget;
        const distance = event.pageX - row.offsetLeft - drag.current.startX;
        if (Math.abs(distance) > 5) drag.current.moved = true;
        row.scrollLeft = drag.current.scrollLeft - distance;
    };
    const stopDrag = () => { drag.current.isDown = false; };
    const handleClickCapture = (event) => {
        const moved = drag.current.moved;
        drag.current.moved = false;
        if (moved && event.detail > 0) {
            event.preventDefault();
            event.stopPropagation();
        }
    };

    return <div {...props}
        className={`overflow-x-auto cursor-grab active:cursor-grabbing select-none [&_button]:cursor-grab [&_button:active]:cursor-grabbing ${className}`}
        onMouseDown={handleMouseDown} onMouseMove={handleMouseMove}
        onMouseUp={stopDrag} onMouseLeave={stopDrag} onClickCapture={handleClickCapture}>
        {children}
    </div>;
}

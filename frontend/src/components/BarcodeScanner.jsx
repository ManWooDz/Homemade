import { useEffect, useId, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

// Module-level chain: serializes start/stop across mounts of this widget so
// React StrictMode's dev double-invoke (mount -> cleanup -> mount, back to
// back, without awaiting the cleanup) can never run two Html5Qrcode camera
// sessions concurrently against getUserMedia.
let scannerTurnstile = Promise.resolve();

// This widget can unmount (e.g. the parent flips away from "scanning" the
// instant a code is detected/submitted) while html5-qrcode's internal
// <video>.play() promise is still pending. Chromium then rejects that
// promise once the element is torn out of the DOM ("play() request was
// interrupted because the media was removed from the document") — a
// benign, Chrome-documented artifact (https://goo.gl/LdLk22) of
// intentional teardown, not a real error, but it surfaces as an uncaught
// rejection. The rejection can land after our own effect cleanup has
// already run, so this is installed once for the page's lifetime rather
// than scoped to a single mount — it only ever swallows this one exact,
// known-benign message.
if (typeof window !== "undefined") {
    window.addEventListener("unhandledrejection", (event) => {
        if (
            typeof event.reason?.message === "string" &&
            event.reason.message.includes("play() request was interrupted")
        ) {
            event.preventDefault();
        }
    });
}

// Pure scanning widget: camera feed + manual-digit fallback. No page chrome,
// no API call — the parent page owns navigation and the barcode-lookup call.
export default function BarcodeScanner({ onDetected }) {
    const [manualCode, setManualCode] = useState("");
    const [cameraError, setCameraError] = useState("");
    const elementId = useId().replace(/:/g, "");
    const onDetectedRef = useRef(onDetected);
    onDetectedRef.current = onDetected;

    useEffect(() => {
        let cancelled = false;
        let startPromise = null;
        const html5QrCode = new Html5Qrcode(elementId);
        const myTurn = scannerTurnstile;

        const ready = myTurn.then(() => {
            if (cancelled) return;
            startPromise = html5QrCode.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 220 },
                (decodedText) => {
                    // Stop after the first hit; the callback otherwise fires
                    // on every decoded frame and would re-trigger lookups.
                    html5QrCode
                        .stop()
                        .catch(() => {})
                        .finally(() => {
                            try {
                                html5QrCode.clear();
                            } catch {
                                // clear() is synchronous and can throw if the
                                // scanner never fully initialized — harmless.
                            }
                            onDetectedRef.current(decodedText);
                        });
                },
                () => {
                    // per-frame "nothing decoded yet" noise, not a real error
                },
            );
            startPromise.catch(() => {
                if (!cancelled) {
                    setCameraError(
                        "เปิดกล้องไม่ได้ ลองพิมพ์เลขบาร์โค้ดด้านล่างแทน",
                    );
                }
            });
        });

        scannerTurnstile = ready
            .then(() => startPromise)
            .catch(() => {});

        return () => {
            cancelled = true;
            scannerTurnstile = ready
                .then(() => startPromise)
                .then(() => html5QrCode.stop())
                .catch(() => {})
                .finally(() => {
                    try {
                        html5QrCode.clear();
                    } catch {
                        // same as above — safe to ignore
                    }
                });
        };
    }, [elementId]);

    const handleManualSubmit = (e) => {
        e.preventDefault();
        const trimmed = manualCode.trim();
        if (!trimmed) return;
        onDetected(trimmed);
    };

    return (
        <div>
            <div
                id={elementId}
                className="w-full aspect-square bg-gray-900 rounded-xl overflow-hidden mb-3"
            />

            {cameraError && (
                <p className="text-sm text-red-500 mb-3">{cameraError}</p>
            )}

            <p className="text-xs text-gray-400 mb-2">
                กล้องเปิดไม่ได้? พิมพ์เลขบาร์โค้ดเอง:
            </p>
            <form onSubmit={handleManualSubmit} className="flex gap-2">
                <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    placeholder="8850999327015"
                    className="flex-1 bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 text-sm outline-none focus:border-[#EF5A3A]"
                    value={manualCode}
                    onChange={(e) => setManualCode(e.target.value)}
                />
                <button
                    type="submit"
                    disabled={!manualCode.trim()}
                    className="bg-[#EF5A3A] text-white px-4 rounded-xl text-sm font-medium disabled:opacity-50"
                >
                    Look up
                </button>
            </form>
        </div>
    );
}

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
        // useBarCodeDetectorIfSupported belongs HERE (2nd constructor arg),
        // not in start()'s config — verified in html5-qrcode's own source
        // (html5-qrcode.js: Html5Qrcode constructor reads it, not start()).
        // Omitting it (as this code did before) silently defaults to true,
        // meaning it tries the browser's native BarcodeDetector API — whose
        // per-format support (EAN/UPC specifically) varies unpredictably
        // across devices/browsers and isn't actually verified by the
        // library before use. Forcing the bundled ZXing-JS decoder instead
        // trades a rare native-speed win for real cross-device consistency.
        const html5QrCode = new Html5Qrcode(elementId, {
            useBarCodeDetectorIfSupported: false,
        });
        const myTurn = scannerTurnstile;

        const ready = myTurn.then(() => {
            if (cancelled) return;
            startPromise = html5QrCode.start(
                { facingMode: "environment" },
                {
                    fps: 10,
                    // A square box crops out most of a 1D barcode's width in
                    // the actual decoded region (verified in html5-qrcode's
                    // own source: foreverScan() draws only this box's pixels
                    // to the decode canvas — nothing outside it is ever
                    // seen, regardless of what the live preview shows). EAN/
                    // UPC barcodes are wide relative to their height, so the
                    // box needs to be too.
                    qrbox: (viewfinderWidth, viewfinderHeight) => ({
                        width: Math.floor(viewfinderWidth * 0.85),
                        height: Math.floor(viewfinderHeight * 0.65),
                    }),
                    // Confirmed via source (html5-qrcode.js start()): when
                    // videoConstraints is set, it REPLACES the first-arg
                    // camera selection entirely — facingMode has to be
                    // repeated here or it's silently dropped. Requesting
                    // higher resolution matters specifically for 1D barcodes
                    // (EAN/UPC): decode reliability scales with how many
                    // pixels the bars actually span, unlike QR codes which
                    // are far more tolerant of low resolution.
                    videoConstraints: {
                        facingMode: "environment",
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                    },
                },
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
            startPromise.then(() => {
                // html5-qrcode's own createVideoElement() snapshots the
                // container's clientWidth ONCE at creation and hardcodes it
                // as an inline px width on the <video> forever — it never
                // re-measures (confirmed: no resize listener in its source).
                // If the container's real width differs even slightly by
                // the time layout settles (e.g. a scrollbar appearing or
                // disappearing between that measurement and final paint),
                // the video is left permanently smaller than its container,
                // showing as a thin dark border. Overriding to fill
                // responsively removes any dependence on that one-time
                // snapshot being exactly right.
                const videoEl = document.getElementById(elementId)?.querySelector("video");
                if (videoEl) {
                    videoEl.style.width = "100%";
                    videoEl.style.height = "100%";
                    videoEl.style.objectFit = "cover";
                }
            });
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
                // html5-qrcode's <video> only gets an explicit width — its
                // height auto-follows the real camera stream's aspect ratio
                // (confirmed 16:9 on the webcam tested against). A square
                // container is taller than that, leaving real empty space
                // below the video (not a shading artifact) — matching the
                // container's own aspect ratio to the camera's fills it.
                className="w-full aspect-video bg-gray-900 rounded-xl overflow-hidden mb-3"
            />

            {cameraError && (
                <p className="text-sm text-red-500 mb-3">{cameraError}</p>
            )}

            {!cameraError && (
                <p className="text-xs text-gray-400 mb-3 text-center">
                    วางบาร์โค้ดในแนวนอน ให้เห็นเต็มแท่งในกรอบ
                </p>
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

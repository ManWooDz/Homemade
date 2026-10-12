import { useCallback, useEffect, useRef, useState } from "react";
import {
    prepareZXingModule,
    Scanner,
} from "@yudiel/react-qr-scanner";
import { isValidBarcode } from "../utils/barcodeValidation";

// Keep these objects outside the component: the scanner treats changed object
// identities as new camera settings and would otherwise restart on each render.
const RETAIL_FORMATS = [
    "ean_13",
    "ean_8",
    "upc_a",
    "upc_e",
    "itf",
    "itf_14",
    "code_128",
];

const CAMERA_CONSTRAINTS = {
    facingMode: "environment",
    width: { ideal: 1920 },
    height: { ideal: 1080 },
    frameRate: { ideal: 30 },
};

const SCANNER_COMPONENTS = {
    finder: true,
    torch: true,
    zoom: true,
    onOff: false,
};

const SCANNER_STYLES = {
    container: {
        width: "100%",
        height: "100%",
        aspectRatio: "16 / 9",
        borderRadius: "0.75rem",
    },
    video: {
        width: "100%",
        height: "100%",
        objectFit: "cover",
    },
};

// Pure scanning widget: camera feed + manual-digit fallback. No page chrome,
// no API call — the parent page owns navigation and the barcode-lookup call.
export default function BarcodeScanner({ onDetected, manualCode, onCodeChange, focusInput }) {
    const [cameraError, setCameraError] = useState("");
    const [codeError, setCodeError] = useState("");
    const manualInput = useRef(null);
    const scanLockedRef = useRef(false);

    useEffect(() => {
        // Start downloading/compiling ZXing-C++ while camera permission and
        // playback are being established, reducing time to the first decode.
        void prepareZXingModule({ fireImmediately: true }).catch(() => {});
    }, []);

    useEffect(() => {
        if (focusInput || cameraError) manualInput.current?.focus();
    }, [focusInput, cameraError]);

    const handleScan = useCallback(
        (detectedCodes) => {
            if (scanLockedRef.current) return;

            const detected = detectedCodes.find(({ rawValue }) =>
                isValidBarcode(rawValue),
            );
            if (!detected) return;

            scanLockedRef.current = true;
            onDetected(detected.rawValue);
        },
        [onDetected],
    );

    const handleCameraError = useCallback(() => {
        setCameraError(
            "เปิดกล้องหรือระบบสแกนไม่ได้ คุณยังพิมพ์เลขหรือเพิ่มวัตถุดิบเองได้",
        );
    }, []);

    const handleManualSubmit = (e) => {
        e.preventDefault();
        const trimmed = manualCode.trim();
        if (!isValidBarcode(trimmed)) {
            setCodeError("กรุณากรอกเลขบาร์โค้ด 8–14 หลัก โดยใช้ตัวเลข 0–9 เท่านั้น");
            manualInput.current?.focus();
            return;
        }
        if (scanLockedRef.current) return;
        scanLockedRef.current = true;
        onDetected(trimmed);
    };

    return (
        <div>
            {!cameraError && <div className="barcode-camera w-full aspect-video bg-gray-900 rounded-xl overflow-hidden mb-3">
                <Scanner
                    onScan={handleScan}
                    onError={handleCameraError}
                    constraints={CAMERA_CONSTRAINTS}
                    formats={RETAIL_FORMATS}
                    components={SCANNER_COMPONENTS}
                    styles={SCANNER_STYLES}
                    retryDelay={50}
                    sound={false}
                />
            </div>}

            {cameraError && (
                <p role="alert" className="text-sm text-red-700 mb-4">{cameraError}</p>
            )}

            {!cameraError && (
                <p className="text-sm text-gray-600 mb-6 text-center">
                    ให้เห็นบาร์โค้ดครบทั้งแถบ ถือกล้องให้นิ่ง ไม่ต้องเข้าใกล้มาก
                </p>
            )}

            <form onSubmit={handleManualSubmit} noValidate>
                <label htmlFor="barcode-code" className="block text-sm font-semibold text-gray-900 mb-1">
                    เลขบาร์โค้ด
                </label>
                <p id="barcode-code-hint" className="text-sm text-gray-600 mb-3">
                    พิมพ์เลข 8–14 หลักใต้บาร์โค้ดแทนการสแกนได้
                </p>
                <div className="flex flex-col min-[360px]:flex-row gap-3">
                <input
                    ref={manualInput}
                    id="barcode-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    pattern="[0-9]{8,14}"
                    aria-invalid={Boolean(codeError)}
                    aria-describedby={codeError ? "barcode-code-hint barcode-code-error" : "barcode-code-hint"}
                    placeholder="เช่น 8850999327015"
                    className="min-w-0 flex-1 min-h-11 bg-gray-50 border border-gray-500 rounded-xl px-3 py-2 text-base placeholder:text-gray-600 focus:outline-2 focus:outline-offset-2 focus:outline-[#B93E25]"
                    value={manualCode}
                    onChange={(e) => {
                        onCodeChange(e.target.value.replace(/[^0-9]/g, ""));
                        setCodeError("");
                    }}
                />
                <button
                    type="submit"
                    disabled={!manualCode.trim()}
                    className="min-h-11 bg-[#B93E25] text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-[#9F341F] disabled:bg-gray-100 disabled:text-gray-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25] transition"
                >
                    ค้นหาสินค้า
                </button>
                </div>
                {codeError && <p id="barcode-code-error" role="alert" className="text-sm text-red-700 mt-3">{codeError}</p>}
            </form>
        </div>
    );
}

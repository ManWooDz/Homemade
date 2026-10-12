import { useEffect, useRef, useState } from "react";
import { ChevronLeft, Loader2 } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import BarcodeScanner from "../components/BarcodeScanner";
import { useAuth } from "../context/AuthContext";
import { toUserFacingBarcodeError } from "../utils/barcodeValidation";

export default function BarcodeScanPage({
    onBack,
    onScanned,
    onAddManually,
    activeTab,
    setActiveTab,
}) {
    const { apiFetch } = useAuth();
    const [phase, setPhase] = useState("scanning"); // "scanning" | "looking-up" | "error"
    const [errorMessage, setErrorMessage] = useState("");
    const [barcode, setBarcode] = useState("");
    const lookup = useRef(null);
    const feedback = useRef(null);

    useEffect(() => () => lookup.current?.abort(), []);

    useEffect(() => {
        if (phase !== "scanning") feedback.current?.focus();
    }, [phase]);

    const handleDetected = async (code) => {
        if (lookup.current) return;
        const controller = new AbortController();
        lookup.current = controller;
        setBarcode(code);
        setErrorMessage("");
        setPhase("looking-up");
        try {
            const response = await apiFetch(
                `/api/barcode-lookup?code=${encodeURIComponent(code)}`,
                { signal: controller.signal },
            );
            const result = await response.json();
            if (controller.signal.aborted) return;
            if (!response.ok) throw new Error("Barcode lookup failed");
            if (result.status === "success" && typeof result.data?.name === "string" && result.data.name.trim()) {
                onScanned(result.data);
            } else {
                setErrorMessage(toUserFacingBarcodeError(result.message));
                setPhase("error");
            }
        } catch {
            if (controller.signal.aborted) return;
            setErrorMessage(toUserFacingBarcodeError());
            setPhase("error");
        } finally {
            if (lookup.current === controller) lookup.current = null;
        }
    };

    const handleRetry = () => {
        setErrorMessage("");
        setPhase("scanning");
    };

    return (
        <div className="h-dvh bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <div className="pt-8 px-6 flex items-center justify-center relative z-20 mb-6">
                    <button
                        type="button"
                        aria-label="กลับไปตู้เย็น"
                        onClick={() => {
                            lookup.current?.abort();
                            onBack();
                        }}
                        className="absolute left-6 w-11 h-11 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]"
                    >
                        <ChevronLeft aria-hidden="true" className="w-6 h-6" />
                    </button>
                    <img
                        src={logo}
                        alt="HomeMade"
                        className="h-18 object-contain"
                    />
                </div>

                <main className="flex-1 min-h-0 overflow-y-auto px-5 pb-36">
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">
                        สแกนบาร์โค้ด
                    </h1>
                    <p className="text-sm text-gray-600 mb-6">
                        ค้นหาสินค้าเพื่อเพิ่มวัตถุดิบเข้าตู้เย็น
                    </p>

                    <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
                        {phase === "looking-up" ? `กำลังค้นหาสินค้าจากบาร์โค้ด ${barcode}` : ""}
                    </p>

                    {phase === "looking-up" && (
                        <div ref={feedback} tabIndex={-1} aria-labelledby="barcode-lookup-status" className="flex flex-col items-center justify-center gap-3 py-10 text-gray-600 focus-visible:outline-2 focus-visible:outline-[#B93E25] rounded-xl">
                            <Loader2 aria-hidden="true" className="w-8 h-8 animate-spin motion-reduce:animate-none" />
                            <p id="barcode-lookup-status" className="text-sm">กำลังค้นหาสินค้า...</p>
                            <p className="text-base text-gray-900 break-all">เลขบาร์โค้ด {barcode}</p>
                        </div>
                    )}

                    {phase === "error" && (
                        <div ref={feedback} tabIndex={-1} aria-labelledby="barcode-lookup-error" className="flex flex-col items-center gap-4 py-6 text-center focus-visible:outline-2 focus-visible:outline-[#B93E25] rounded-xl">
                            <p id="barcode-lookup-error" role="alert" className="text-sm text-red-700">
                                {errorMessage}
                            </p>
                            <p className="text-base text-gray-900 break-all">เลขบาร์โค้ด {barcode}</p>
                            <div className="flex flex-col gap-3 w-full">
                                <button
                                    type="button"
                                    onClick={() => handleDetected(barcode)}
                                    className="min-h-11 px-4 py-3 rounded-full text-sm font-bold text-white bg-[#B93E25] hover:bg-[#9F341F] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25] transition"
                                >
                                    ค้นหาอีกครั้ง
                                </button>
                                <button
                                    type="button"
                                    onClick={handleRetry}
                                    className="min-h-11 px-4 py-3 rounded-full text-sm font-bold text-gray-700 border border-gray-300 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25]"
                                >
                                    แก้เลขหรือสแกนใหม่
                                </button>
                            </div>
                        </div>
                    )}

                    {phase === "scanning" && (
                        <BarcodeScanner
                            onDetected={handleDetected}
                            manualCode={barcode}
                            onCodeChange={setBarcode}
                            focusInput={Boolean(barcode)}
                        />
                    )}
                    <button
                        type="button"
                        onClick={() => {
                            lookup.current?.abort();
                            onAddManually();
                        }}
                        className="mt-6 w-full min-h-11 px-4 py-3 border border-[#B93E25] rounded-full text-sm font-bold text-[#B93E25] hover:bg-[#FDECE5] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25] transition"
                    >
                        เพิ่มวัตถุดิบเอง
                    </button>
                </main>

                <BottomMenu activeTab={activeTab} setActiveTab={(tab) => {
                    lookup.current?.abort();
                    setActiveTab(tab);
                }} />
            </div>
        </div>
    );
}

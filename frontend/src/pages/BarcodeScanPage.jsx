import { useState } from "react";
import { ChevronLeft, Loader2 } from "lucide-react";
import logo from "../assets/HomeMade_Logo.png";
import BottomMenu from "../components/bottomMenu";
import BarcodeScanner from "../components/BarcodeScanner";
import { useAuth } from "../context/AuthContext";

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
    const [scannerKey, setScannerKey] = useState(0);

    const handleDetected = async (code) => {
        setPhase("looking-up");
        try {
            const response = await apiFetch(
                `/api/barcode-lookup?code=${encodeURIComponent(code)}`,
            );
            const result = await response.json();
            if (result.status === "success") {
                onScanned(result.data);
            } else {
                setErrorMessage(result.message || "ไม่พบสินค้านี้");
                setPhase("error");
            }
        } catch (error) {
            setErrorMessage("ค้นหาบาร์โค้ดไม่สำเร็จ");
            setPhase("error");
        }
    };

    const handleRetry = () => {
        setErrorMessage("");
        setScannerKey((k) => k + 1);
        setPhase("scanning");
    };

    return (
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                <div className="pt-8 px-6 flex items-center justify-center relative z-20 mb-6">
                    <button
                        onClick={onBack}
                        className="absolute left-6 w-10 h-10 bg-[#EF5A3A] text-white rounded-full flex items-center justify-center shadow-md"
                    >
                        <ChevronLeft className="w-6 h-6" />
                    </button>
                    <img
                        src={logo}
                        alt="HomeMade"
                        className="h-18 object-contain"
                    />
                </div>

                <div className="flex-1 overflow-y-auto px-5 pb-32">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">
                        Scan Barcode
                    </h2>

                    {phase === "looking-up" && (
                        <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-500">
                            <Loader2 className="w-8 h-8 animate-spin" />
                            <p className="text-sm">กำลังค้นหาสินค้า...</p>
                        </div>
                    )}

                    {phase === "error" && (
                        <div className="flex flex-col items-center gap-4 py-10 text-center">
                            <p className="text-sm text-red-500">
                                {errorMessage}
                            </p>
                            <div className="flex gap-3 w-full">
                                <button
                                    onClick={handleRetry}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-gray-600 border border-gray-300"
                                >
                                    ลองใหม่
                                </button>
                                <button
                                    onClick={onAddManually}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-white bg-[#EF5A3A] shadow-md hover:bg-orange-600 transition"
                                >
                                    เพิ่มเอง
                                </button>
                            </div>
                        </div>
                    )}

                    {phase === "scanning" && (
                        <BarcodeScanner
                            key={scannerKey}
                            onDetected={handleDetected}
                        />
                    )}
                </div>

                <BottomMenu activeTab={activeTab} setActiveTab={setActiveTab} />
            </div>
        </div>
    );
}

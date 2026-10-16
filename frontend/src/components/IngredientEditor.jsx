import { useState, useRef } from "react";
import { useLocale } from "../context/LocaleContext";
import { useAuth } from "../context/AuthContext";
import { toUserIngredientCreate } from "../utils/ingredientPayload";
import { QUANTITY_UNITS } from "../utils/quantityUnits";

export default function IngredientEditor({ ingredient, onSaved, onCancel, onBusyChange }) {
    const { t } = useLocale();
    const { apiFetch } = useAuth();
    const [name, setName] = useState(ingredient.name);
    const [category, setCategory] = useState(ingredient.category || "Other");
    const [quantityAmount, setQuantityAmount] = useState(String(ingredient.quantity_amount ?? ""));
    const [quantityUnit, setQuantityUnit] = useState(ingredient.quantity_unit || "");
    const [expiryDate, setExpiryDate] = useState(ingredient.expiry_date || "");
    const [busy, setBusy] = useState(false);
    const pending = useRef(false);
    const [error, setError] = useState("");
    const inputClass = "mt-1 w-full min-h-11 rounded-full border border-gray-300 px-4 py-2 bg-white text-gray-900 focus:outline-2 focus:outline-[#EF5A3A]";

    const save = async (event) => {
        event.preventDefault();
        if (pending.current) return;
        if (!name.trim()) { setError("กรุณาระบุชื่อวัตถุดิบ"); return; }
        const amount = quantityAmount.trim();
        if (amount && !(Number.isFinite(Number(amount)) && Number(amount) > 0 && Number(amount) <= 100000)) {
            setError("ปริมาณต้องมากกว่า 0 และไม่เกิน 100,000"); return;
        }
        pending.current = true;
        setBusy(true);
        onBusyChange(true);
        setError("");
        try {
            const payload = toUserIngredientCreate({ name, category, expiryDate, quantityAmount, quantityUnit });
            const response = await apiFetch(`/api/user-ingredients/${ingredient.id}`, {
                method: "PUT", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: payload.name, category: payload.category, expiry_date: payload.expiry_date, quantity_amount: payload.quantity_amount, quantity_unit: payload.quantity_unit }),
            });
            const result = await response.json();
            if (!response.ok || result.status !== "success" || result.data?.id !== ingredient.id) {
                setError(response.status === 404 ? "ไม่พบวัตถุดิบนี้ กลับไปโหลดตู้เย็นใหม่" : "บันทึกวัตถุดิบไม่สำเร็จ ข้อมูลที่แก้ยังอยู่ กรุณาลองอีกครั้ง");
                return;
            }
            onSaved(result.data);
        } catch {
            setError("บันทึกวัตถุดิบไม่สำเร็จ ข้อมูลที่แก้ยังอยู่ กรุณาลองอีกครั้ง");
        } finally {
            pending.current = false;
            setBusy(false);
            onBusyChange(false);
        }
    };

    return <form onSubmit={save} aria-label={t("แก้ไขวัตถุดิบ")}>
        <h3 className="text-xl font-bold text-gray-900 mb-4">{t("แก้ไขวัตถุดิบ")}</h3>
        <fieldset disabled={busy} className="space-y-4 disabled:opacity-60">
            <label className="block text-sm font-semibold text-gray-700">{t("ชื่อวัตถุดิบ")}<input autoFocus required maxLength={200} value={name} onChange={event => setName(event.target.value)} className={inputClass} /></label>
            <label className="block text-sm font-semibold text-gray-700">{t("Category")}<select required value={category} onChange={event => setCategory(event.target.value)} className={inputClass}>
                {["Meat & poultry", "Vegetables", "Fruits", "Other"].map(value => <option key={value} value={value}>{t(value)}</option>)}
            </select></label>
            <div className="grid grid-cols-2 gap-3">
                <label className="block text-sm font-semibold text-gray-700 min-w-0">{t("ปริมาณ")}<input type="number" min="0" max="100000" step="any" value={quantityAmount} onChange={event => { setQuantityAmount(event.target.value); if (!event.target.value) setQuantityUnit(""); }} className={inputClass} /></label>
                <label className="block text-sm font-semibold text-gray-700 min-w-0">{t("หน่วย")}<select disabled={!quantityAmount.trim()} value={quantityUnit} onChange={event => setQuantityUnit(event.target.value)} className={inputClass}><option value="">{t("ไม่ได้ระบุ")}</option>{QUANTITY_UNITS.map(value => <option key={value} value={value}>{t(value)}</option>)}</select></label>
            </div>
            <label className="block text-sm font-semibold text-gray-700">{t("วันหมดอายุ (โดยประมาณ)")}<input type="date" value={expiryDate} onChange={event => setExpiryDate(event.target.value)} className={`${inputClass} min-w-0`} /></label>
            {expiryDate && <button type="button" onClick={() => setExpiryDate("")} className="min-h-11 text-sm text-gray-700 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-[#EF5A3A]">{t("ล้างวันหมดอายุ")}</button>}
            <p className="text-sm text-gray-600">{t("เว้นปริมาณหรือวันหมดอายุว่างได้ หากยังไม่ทราบ")}</p>
            {ingredient.nutrition_data && <p className="text-sm text-gray-600">{t("ข้อมูลโภชนาการยังอ้างอิงสินค้าที่สแกนเดิม การแก้ชื่อไม่เปลี่ยนข้อมูลนี้")}</p>}
            <div className="flex gap-3 pt-2">
                <button type="button" onClick={onCancel} className="flex-1 min-h-11 rounded-full border border-gray-300 text-gray-700 font-semibold focus-visible:outline-2 focus-visible:outline-[#EF5A3A]">{t("ยกเลิก")}</button>
                <button type="submit" className="flex-1 min-h-11 rounded-full bg-[#EF5A3A] text-white font-semibold focus-visible:outline-2 focus-visible:outline-gray-900">{t(busy ? "กำลังบันทึก..." : "บันทึก")}</button>
            </div>
        </fieldset>
        {error && <p role="alert" className="text-sm text-red-700 mt-3">{t(error)}</p>}
    </form>;
}

import { useLocale } from "../context/LocaleContext";
import { ChevronDown } from "lucide-react";

const MACROS = [
    ["calories", "แคลอรี่", "kcal"],
    ["carbs_g", "คาร์โบไฮเดรต", "g", "bg-[#e4fbec]"],
    ["protein_g", "โปรตีน", "g", "bg-[#eaf3ff]"],
    ["fat_g", "ไขมัน", "g", "bg-[#fffad8]"],
];
const EXTRAS = [["sugar_g", "น้ำตาล", "g"], ["sodium_mg", "โซเดียม", "mg"], ["fiber_g", "ใยอาหาร", "g"], ["vitamin_c_mg", "วิตามินซี", "mg"]];
const hasValue = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
const BASE_REASONS = {
    inputs_incomplete: "ข้อมูลปริมาณ จำนวนที่ หรือโภชนาการวัตถุดิบไม่ครบ จึงยังคำนวณไม่ได้",
    source_unverified: "แหล่งข้อมูลของวัตถุดิบบางรายการยังไม่ผ่านการยืนยัน",
    proxy_composition: "วัตถุดิบบางรายการใช้ข้อมูลโภชนาการของวัตถุดิบใกล้เคียง",
    derived_macros: "สารอาหารบางค่าได้จากการคำนวณเพิ่มเติมในชุดข้อมูล",
    constant_unverified: "วัตถุดิบบางรายการใช้ค่าคงที่ที่ยังไม่ยืนยันแหล่งข้อมูล",
};

export default function RecipeNutrition({ recipe, compact = false }) {
    const { t, locale } = useLocale();
    const nutrition = recipe.nutrition;
    const computed = recipe.computed_nutrition;
    const estimate = recipe.llm_estimated_nutrition;
    const baseCalculation = recipe.nutrition_origin === "base_calculation";
    const unavailable = baseCalculation && !computed;
    const partial = recipe.nutrition_partially_estimated === true;
    const calculated = recipe.nutrition_partially_estimated === false && computed && MACROS.every(([key]) => hasValue(computed[key]));
    const status = unavailable ? "ยังคำนวณไม่ได้" : calculated ? "คำนวณจากฐานข้อมูล" : baseCalculation ? "คำนวณแล้ว แต่ข้อมูลยังมีข้อจำกัด" : partial ? "ยังมีค่าประมาณ" : "ไม่ระบุวิธีคำนวณ";
    const format = (value, unit) => hasValue(value)
        ? `${new Intl.NumberFormat(locale === "en" ? "en-US" : "th-TH", { maximumFractionDigits: 1 }).format(value)} ${t(unit)}`
        : "—";
    const basis = (data) => data?.basis === "per_serving" ? t("ต่อ 1 ที่") : t("ไม่ระบุฐานปริมาณ");

    return (
        <section className="recipe-nutrition mb-6" aria-label={t("Nutrition")}>
            <h3 className="text-xl font-bold text-gray-900 mb-3">{t("Nutrition")}</h3>
            <div className="mb-4 rounded-2xl border border-gray-200 p-4 text-sm text-gray-700">
                <p className="font-semibold text-gray-900">{t(status)}</p>
                <p className="mt-1">{t(baseCalculation
                    ? unavailable
                        ? "ต้องมีปริมาณวัตถุดิบ จำนวนที่ และข้อมูลสารอาหารครบก่อนคำนวณ ไม่ใช้ค่า AI เดิมแทน"
                        : "คำนวณใหม่จากปริมาณวัตถุดิบในสูตรและจำนวนที่ ไม่ใช้ค่าโภชนาการเดิม"
                    : calculated
                    ? "ใช้ผลคำนวณจากวัตถุดิบและปริมาณในสูตร ค่าจริงอาจต่างตามวิธีปรุง"
                    : partial
                        ? "ตัวเลขหลักเป็นค่าประมาณของ AI ผลคำนวณยังไม่ผ่านเงื่อนไขข้อมูลครบถ้วน"
                        : "รายการนี้ไม่มีสถานะยืนยันแหล่งคำนวณ จึงยังยืนยันความครบถ้วนไม่ได้")}</p>
                {!compact && <p className="mt-2 font-medium">{basis(nutrition)}</p>}
                {MACROS.some(([key]) => !hasValue(nutrition?.[key])) && <p className="mt-1">{t("เครื่องหมาย — หมายถึงไม่มีข้อมูล ไม่ใช่ศูนย์")}</p>}
            </div>
            <div className="recipe-calorie-summary bg-[#FFF6F2] rounded-3xl p-5 mb-3">
                <div>
                <p className="text-3xl font-semibold text-gray-900 tabular-nums break-words">{format(nutrition?.calories, "kcal")}</p>
                <p className="text-sm text-gray-700 mt-1">{t("แคลอรี่")}</p>
                </div>
                {compact && <p className="recipe-calorie-basis">{basis(nutrition)}</p>}
            </div>
            <div className="grid grid-cols-3 gap-2">
                {MACROS.slice(1).map(([key, label, unit, color]) => (
                    <div key={key} className={`${color} rounded-3xl px-2 py-4 text-center min-w-0`}>
                        <p className="text-lg font-bold text-gray-900 tabular-nums break-words">{format(nutrition?.[key], unit)}</p>
                        <p className="text-xs text-gray-700 mt-1">{t(key === "carbs_g" ? "คาร์บ" : label)}</p>
                    </div>
                ))}
            </div>
            {EXTRAS.some(([key]) => hasValue(nutrition?.[key])) && <dl className="mt-4 space-y-2 text-sm">
                {EXTRAS.filter(([key]) => hasValue(nutrition?.[key])).map(([key, label, unit]) => <div className="flex justify-between gap-3" key={key}><dt>{t(label)}</dt><dd className="tabular-nums">{format(nutrition[key], unit)}</dd></div>)}
            </dl>}
            <details className="group mt-4 border-t border-gray-200 pt-2">
                <summary className="min-h-11 flex items-center justify-between gap-2 cursor-pointer text-sm font-semibold text-gray-900 rounded-lg focus-visible:outline-2 focus-visible:outline-[#EF5A3A]">{t("ดูรายละเอียดการคำนวณ")}<ChevronDown aria-hidden="true" className="w-4 h-4 shrink-0 group-open:rotate-180" /></summary>
                <div className="pb-2 text-sm text-gray-700 space-y-4">
                    {[ [computed, partial || !calculated ? "ผลคำนวณที่ยังไม่ยืนยันความครบถ้วน" : "ผลคำนวณจากฐานข้อมูล"], [estimate, "ค่าประมาณจาก AI"] ].filter(([data]) => data).map(([data, title]) => (
                        <div key={title}>
                            <h4 className="font-semibold text-gray-900">{t(title)}</h4>
                            <p className="mb-2">{basis(data)}</p>
                            <dl className="space-y-1">{MACROS.map(([key, label, unit]) => <div key={key} className="flex justify-between gap-3"><dt>{t(label)}</dt><dd className="tabular-nums">{format(data[key], unit)}</dd></div>)}</dl>
                        </div>
                    ))}
                    {!computed && <p>{t("ไม่มีผลคำนวณจากฐานข้อมูลให้เปรียบเทียบ")}</p>}
                    {baseCalculation ? <>
                        {Array.isArray(recipe.nutrition_calculation_reasons) && recipe.nutrition_calculation_reasons.length > 0 && <ul className="list-disc pl-5 space-y-1">{[...new Set(recipe.nutrition_calculation_reasons)].filter(code => Object.hasOwn(BASE_REASONS, code)).map(code => <li key={code}>{t(BASE_REASONS[code])}</li>)}</ul>}
                        <p>{t("เป็นผลรวมสารอาหารจากวัตถุดิบ ยังไม่ปรับการสูญเสียจากการปรุงหรือการดูดซับน้ำมัน")}</p>
                    </> : <p>{t("ระบบไม่ได้บันทึกเหตุผลหรือแหล่งข้อมูลรายวัตถุดิบไว้ในรายการนี้")}</p>}
                </div>
            </details>
        </section>
    );
}

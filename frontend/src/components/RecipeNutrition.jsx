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
const INGREDIENT_SOURCES = {
    product_label: "ฉลากสินค้า", llm_estimate: "ค่าประมาณจาก AI", unresolved: "ยังหาแหล่งข้อมูลไม่ได้",
    hardcoded_zero: "ค่าคงที่โดยประมาณ", INMU: "INMU", USDA: "USDA",
};
const INGREDIENT_STATUSES = { calculated: "คำนวณแล้ว", estimated: "ยังมีค่าประมาณ", incomplete: "ข้อมูลไม่ครบ" };
const INGREDIENT_REASONS = {
    ...BASE_REASONS,
    assumed_raw_potato_weight: "ใช้ข้อมูลมันฝรั่งดิบโดยสมมติว่าชั่งก่อนปรุง",
    quantity_unresolved: "ยังแปลงปริมาณในสูตรเป็นหน่วยที่ใช้คำนวณไม่ได้",
    quantity_conversion_unverified: "ใช้การแปลงปริมาณโดยประมาณ",
    unsupported_nutrition_basis: "ฐานปริมาณของแหล่งข้อมูลยังใช้คำนวณรายการนี้ไม่ได้",
    macro_incomplete: "ข้อมูลสารอาหารหลักไม่ครบ",
    composition_unavailable: "ยังไม่มีค่าประมาณโภชนาการที่ใช้ได้",
    composition_estimated: "ใช้ค่าโภชนาการที่ AI ประมาณจากวัตถุดิบ",
    product_label_unavailable: "ไม่มีข้อมูลฉลากที่ใช้คำนวณได้",
    product_label_incomplete: "ข้อมูลสารอาหารบนฉลากไม่ครบ",
    product_quantity_unresolved: "ปริมาณในสูตรไม่ชัดเจนพอที่จะใช้ข้อมูลฉลาก",
    product_conversion_unavailable: "ไม่มีหลักฐานแปลงหน่วยของสินค้านี้",
    product_label_conflict: "ข้อมูลฉลากของสินค้านี้ขัดกัน",
    product_legacy_basis: "ข้อมูลบาร์โค้ดเดิมไม่ได้ระบุฐานปริมาณชัดเจน",
    product_relink_required: "ต้องสแกนยืนยันสินค้านี้อีกครั้ง",
};
const quantityLabel = (unit, locale) => unit === "ml" ? (locale === "en" ? "mL" : "มล.") : (locale === "en" ? "g" : "กรัม");

export default function RecipeNutrition({ recipe, compact = false }) {
    const { t, locale } = useLocale();
    const nutrition = recipe.nutrition;
    const computed = recipe.computed_nutrition;
    const estimate = recipe.llm_estimated_nutrition;
    const target = recipe.protein_target_result;
    const ingredientEvidence = Array.isArray(recipe.nutrition_ingredient_evidence)
        ? recipe.nutrition_ingredient_evidence.filter((item) => item && typeof item === "object") : [];
    const baseCalculation = recipe.nutrition_origin === "base_calculation";
    const unavailable = baseCalculation && !computed;
    const partial = recipe.nutrition_partially_estimated === true;
    const calculated = recipe.nutrition_partially_estimated === false && computed && MACROS.every(([key]) => hasValue(computed[key]));
    const hasProductLabel = ingredientEvidence.some(({ source }) => source === "product_label");
    const hasOtherSource = ingredientEvidence.some(({ source }) => source !== "product_label");
    let calculatedStatus = "คำนวณจากฐานข้อมูล";
    let calculatedTitle = "ผลคำนวณจากฐานข้อมูล";
    if (hasProductLabel && hasOtherSource) {
        calculatedStatus = "คำนวณจากฉลากสินค้าและฐานข้อมูล";
        calculatedTitle = "ผลคำนวณจากฉลากสินค้าและฐานข้อมูล";
    } else if (hasProductLabel) {
        calculatedStatus = "คำนวณจากฉลากสินค้า";
        calculatedTitle = "ผลคำนวณจากฉลากสินค้า";
    }
    const status = unavailable ? "ยังคำนวณไม่ได้" : calculated ? calculatedStatus : baseCalculation ? "คำนวณแล้ว แต่ข้อมูลยังมีข้อจำกัด" : partial ? "ยังมีค่าประมาณ" : "ไม่ระบุวิธีคำนวณ";
    const format = (value, unit) => hasValue(value)
        ? `${new Intl.NumberFormat(locale === "en" ? "en-US" : "th-TH", { maximumFractionDigits: 1 }).format(value)} ${t(unit)}`
        : "—";
    const basis = (data) => data?.basis === "per_serving" ? t("ต่อ 1 ที่") : t("ไม่ระบุฐานปริมาณ");
    const canCompareProtein = (target?.status === "calculated" || target?.status === "estimated")
        && hasValue(target.computed_g_per_serving) && Number.isFinite(target.difference_g_per_serving);

    return (
        <section className="recipe-nutrition mb-6" aria-label={t("Nutrition")}>
            <h3 className="text-xl font-bold text-gray-900 mb-3">{t("Nutrition")}</h3>
            {hasValue(target?.target_g_per_serving) && <div className="mb-4 rounded-2xl border border-gray-200 p-4 text-sm text-gray-700">
                <p className="font-semibold text-gray-900">{t("เป้าโปรตีนต่อเสิร์ฟ: {amount}", { amount: format(target.target_g_per_serving, "g") })}</p>
                {canCompareProtein ? <>
                    <p>{t(target.status === "estimated" ? "โปรตีนโดยประมาณ: {amount}" : "โปรตีนที่คำนวณได้: {amount}", { amount: format(target.computed_g_per_serving, "g") })}</p>
                    <p>{t(target.difference_g_per_serving > 0 ? "สูงกว่าเป้า {amount}" : target.difference_g_per_serving < 0 ? "ต่ำกว่าเป้า {amount}" : "ส่วนต่างจากเป้า {amount}", { amount: format(Math.abs(target.difference_g_per_serving), "g") })}</p>
                </> : <p>{t("ข้อมูลโปรตีนไม่พอสำหรับเปรียบเทียบ")}</p>}
            </div>}
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
                    {[ [computed, calculated ? calculatedTitle : "ผลคำนวณที่ยังไม่ยืนยันความครบถ้วน"], [estimate, "ค่าประมาณจาก AI"] ].filter(([data]) => data).map(([data, title]) => (
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
                    </> : ingredientEvidence.length ? <div>
                        <h4 className="font-semibold text-gray-900">{t("แหล่งข้อมูลรายวัตถุดิบ")}</h4>
                        <ul className="divide-y divide-gray-200">
                            {ingredientEvidence.map((item, index) => <li key={index} className="py-2 wrap-anywhere">
                                <p className="font-medium text-gray-900">{item.raw || item.ingredient}</p>
                                <p>{t(Object.hasOwn(INGREDIENT_SOURCES, item.source) ? INGREDIENT_SOURCES[item.source] : "แหล่งข้อมูลทั่วไป")}
                                    {Object.hasOwn(INGREDIENT_STATUSES, item.status) && ` · ${t(INGREDIENT_STATUSES[item.status])}`}</p>
                                {typeof item.source_ref === "string" && <p>{item.source_ref}</p>}
                                {item.product_name && <p>{item.product_name}</p>}
                                {item.source === "product_label" && <>
                                    {item.label_source === "manufacturer" && <p>{t("ข้อมูลจากผู้ผลิต")}</p>}
                                    {hasValue(item.basis?.quantity) && <p>{t("ฉลากต่อ {quantity}", { quantity: `${item.basis.quantity} ${quantityLabel(item.basis.unit, locale)}` })}</p>}
                                    {hasValue(item.converted_quantity?.amount) && <p>{t("ปริมาณในสูตร {quantity}", { quantity: `${item.converted_quantity.amount} ${quantityLabel(item.converted_quantity.unit, locale)}` })}</p>}
                                    {item.method === "reviewed_product_conversion" && <p>{t("แปลงหน่วยตามหลักฐานของสินค้า")}</p>}
                                    {typeof item.conversion_evidence?.source_url === "string" && item.conversion_evidence.source_url.startsWith("https://") &&
                                        <a href={item.conversion_evidence.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{t("แหล่งอ้างอิงการแปลงหน่วย")}</a>}
                                </>}
                                {Object.hasOwn(INGREDIENT_REASONS, item.reason) && <p>{t(INGREDIENT_REASONS[item.reason])}</p>}
                            </li>)}
                        </ul>
                    </div> : <p>{t("ระบบไม่ได้บันทึกเหตุผลหรือแหล่งข้อมูลรายวัตถุดิบไว้ในรายการนี้")}</p>}
                </div>
            </details>
        </section>
    );
}

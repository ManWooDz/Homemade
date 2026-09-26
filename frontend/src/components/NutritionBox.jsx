// Read-only display of raw Open Food Facts nutrition data — separate from
// (never fed into) the app's own nutrition engine, hence the explicit
// source label. Missing individual macros (real OFF data is often partial)
// render as "-" rather than hiding the whole box.
export default function NutritionBox({ nutrition }) {
    if (!nutrition) return null;

    const rows = [
        ["แคลอรี่", nutrition.calories, "kcal"],
        ["โปรตีน", nutrition.protein_g, "g"],
        ["คาร์โบไฮเดรต", nutrition.carbs_g, "g"],
        ["ไขมัน", nutrition.fat_g, "g"],
    ];

    return (
        <div className="bg-gray-50 border border-gray-200 rounded-2xl p-4">
            <h3 className="text-sm font-bold text-gray-700 mb-2">
                โภชนาการต่อ 100 ก./มล. (จาก Open Food Facts)
            </h3>
            <div className="flex flex-col gap-1">
                {rows.map(([label, value, unit]) => (
                    <div
                        key={label}
                        className="flex justify-between text-sm text-gray-600"
                    >
                        <span>{label}</span>
                        <span className="font-medium text-gray-800">
                            {value != null ? `${value} ${unit}` : "-"}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

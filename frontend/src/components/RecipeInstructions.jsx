import { useLocale } from "../context/LocaleContext";
import { Flame } from "lucide-react";

export default function RecipeInstructions({ instructions, compact = false }) {
  const { t } = useLocale();
  if (!Array.isArray(instructions) || instructions.length === 0) return null;
  return (
    <section className="recipe-instructions mb-6" aria-label={t("วิธีทำ")}>
      <h3 className="text-xl font-medium mb-4 flex items-center gap-2">{!compact && <Flame className="w-5 h-5 text-[#EF5A3A]" />}{t("วิธีทำ")}</h3>
      <ol className="recipe-steps flex flex-col gap-4">
        {instructions.map((step, index) => {
          const cleaned = step.replace(/^\s*\d+[.)]\s*/, "");
          const [title, ...lines] = cleaned.split("\n");
          return (
            <li key={index} className="flex gap-4">
              <span className="recipe-step-number w-8 h-8 rounded-full bg-orange-100 text-[#EF5A3A] font-bold flex items-center justify-center shrink-0" aria-hidden="true">{index + 1}</span>
              <div className="min-w-0 flex-1 text-gray-700 leading-relaxed">{compact && lines.length > 0 ? <><h4 className="font-semibold">{title}</h4><p>{lines.join("\n")}</p></> : <p>{cleaned}</p>}</div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

import { useEffect, useState } from "react";
import { Carrot, SlidersHorizontal, CookingPot, ClipboardCheck } from "lucide-react";
import { useLocale } from "../context/LocaleContext";
import PageShell from "./PageShell";
import logo from "../assets/HomeMade_Logo.png";

// These describe the request, not live pipeline progress; the API has no stage events.
const RECIPE_NOTES = [
  { icon: Carrot, text: "เริ่มต้นจากวัตถุดิบที่คุณเลือก" },
  { icon: SlidersHorizontal, text: "นำความต้องการของคุณมาปรับสูตร" },
  { icon: CookingPot, text: "เรียบเรียงส่วนผสมและวิธีทำ" },
  { icon: ClipboardCheck, text: "ตรวจทานสูตรก่อนแสดงผล" },
];

export default function RecipeGenerating() {
  const { t } = useLocale();
  const [noteIndex, setNoteIndex] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNoteIndex(index => (index + 1) % RECIPE_NOTES.length);
    }, 3500);
    return () => window.clearInterval(interval);
  }, []);

  const { icon: Icon, text } = RECIPE_NOTES[noteIndex];

  return (
    <PageShell contained className="recipe-generating" frameClassName="px-6">
      <header className="flex shrink-0 justify-center pt-8">
        <img src={logo} alt="HomeMade" width="72" height="72" className="h-18 w-18 object-contain" />
      </header>
      <main aria-labelledby="recipe-generating-title" className="scrollbar-hide flex min-h-0 flex-1 flex-col overflow-y-auto py-8">
        <div className="my-auto flex shrink-0 flex-col items-center py-6 text-center">
          <div className="recipe-generating-illustration" aria-hidden="true">
            <Icon key={noteIndex} className="recipe-generating-swap h-16 w-16" strokeWidth={1.5} />
          </div>
          <div role="status" className="recipe-generating-status mt-8">
            <h1 id="recipe-generating-title" className="text-2xl font-bold leading-normal text-gray-900">
              {t("กำลังสร้างสูตรอาหาร...")}
            </h1>
          </div>
          <p className="mt-3 max-w-80 text-base leading-relaxed text-gray-600">
            {t("AI กำลังสร้างสูตรจากวัตถุดิบและความต้องการของคุณ")}
          </p>
          <div className="recipe-generating-dots mt-6 flex gap-2" aria-hidden="true">
            <span /><span /><span />
          </div>
          <div className="recipe-generating-note mt-8 w-full max-w-80 border-t border-[#fdece5] pt-5">
            <p className="text-caption text-gray-500">{t("สิ่งที่ AI พิจารณาระหว่างสร้างสูตร")}</p>
            <p key={noteIndex} className="recipe-generating-swap mt-2 min-h-14 text-base font-medium leading-relaxed text-[#9f351f]">
              {t(text)}
            </p>
          </div>
        </div>
      </main>
    </PageShell>
  );
}
